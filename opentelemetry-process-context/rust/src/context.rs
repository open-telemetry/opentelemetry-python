// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

//! Publication of the process context to a memory region that out of process
//! readers (e.g. the OpenTelemetry eBPF Profiler) can discover and read.
//!
//! The layout follows the OpenTelemetry "Process Context" specification: a fixed
//! 32-byte header mapping named `OTEL_CTX` and backed by a `memfd` on Linux
//! (visible in `/proc/<pid>/maps`), with the payload living out of band in a
//! heap allocated buffer.

use std::ffi::c_void;
use std::num::NonZeroUsize;
use std::ptr::NonNull;
use std::sync::atomic::{AtomicU64, Ordering};

use parking_lot::Mutex;

use nix::sys::mman::{MapFlags, ProtFlags, mmap_anonymous};
use nix::time::{ClockId, clock_gettime};
use pyo3::PyErr;
use pyo3::exceptions::{PyOSError, PyRuntimeError};

#[cfg(target_os = "linux")]
use nix::sys::memfd::{MFdFlags, memfd_create};
#[cfg(target_os = "linux")]
use nix::sys::mman::mmap;

#[cfg(target_os = "linux")]
const PR_SET_VMA: nix::libc::c_int = 0x53564d41;
#[cfg(target_os = "linux")]
const PR_SET_VMA_ANON_NAME: nix::libc::c_ulong = 0;

/// 8 byte signature stamped at the start of the header.
const SIGNATURE: [u8; 8] = *b"OTEL_CTX";
/// Format version. `2` is the first stable version (`1` is for development).
const VERSION: u32 = 2;
/// Size of the header mapping in bytes. The payload lives on the heap.
const HEADER_SIZE: usize = std::mem::size_of::<Header>();

/// The process context header.
#[repr(C)]
struct Header {
    signature: [u8; 8],
    version: u32,
    payload_size: u32,
    monotonic_published_at_ns: AtomicU64,
    payload: u64,
}

/// A published mapping.
struct Region {
    ptr: NonNull<c_void>,
    #[allow(unused)]
    payload: Vec<u8>,
}

// SAFETY: all access goes through `MAPPING` (a `Mutex`), which serializes
// reads and writes. The pointer lives for the process lifetime.
unsafe impl Send for Region {}

/// The single active process context for this process, if any.
static MAPPING: Mutex<Option<Region>> = Mutex::new(None);

/// Register the `pthread_atfork` handlers that keep [`MAPPING`] fork-safe.
///
/// Idempotent: only the first call registers the handlers. Without these, a
/// forked child inherits the parent's `MAPPING` state while the underlying
/// header mapping is gone (stripped by `MADV_DONTFORK` on Linux, or merely
/// stale elsewhere), so a `publish()` in the child would dereference a pointer
/// into an unmapped region and crash.
pub fn register_fork_handlers() {
    static REGISTERED: std::sync::Once = std::sync::Once::new();
    REGISTERED.call_once(|| {
        // SAFETY: the handlers are valid `'static` `extern "C"` functions.
        unsafe {
            nix::libc::pthread_atfork(
                Some(before_fork),
                Some(after_fork_parent),
                Some(after_fork_child),
            );
        }
    });
}

/// `pthread_atfork` prepare handler: acquire the mapping mutex so no other
/// thread holds it across the fork, then forget the guard so the lock stays
/// held into the parent/child handlers, which release it via `force_unlock`.
extern "C" fn before_fork() {
    std::mem::forget(MAPPING.lock());
}

/// `pthread_atfork` parent handler: release the lock taken in [`before_fork`].
extern "C" fn after_fork_parent() {
    // SAFETY: `before_fork` acquired the lock and forgot its guard, so this
    // thread logically owns the lock.
    unsafe { MAPPING.force_unlock() };
}

/// `pthread_atfork` child handler: discard the inherited mapping (the child
/// never received the live header mapping) so the child starts from the
/// pristine "never published" state, then release the lock.
extern "C" fn after_fork_child() {
    // SAFETY: the child is single threaded here and the lock is held from
    // `before_fork`, so this is exclusive access to the protected data.
    let mapping = unsafe { &mut *MAPPING.data_ptr() };
    if let Some(region) = mapping.take() {
        // On non-Linux the mapping was inherited (no `MADV_DONTFORK`), so unmap
        // it. On Linux the child never received the mapping, so the pointer is
        // simply abandoned.
        #[cfg(not(target_os = "linux"))]
        // SAFETY: `region.ptr`/`HEADER_SIZE` describe the inherited mapping.
        unsafe {
            let _ = nix::sys::mman::munmap(region.ptr, HEADER_SIZE);
        }
        // `region.payload` (the inherited `Vec<u8>` copy) is dropped here.
        drop(region);
    }
    // SAFETY: release the lock acquired (and forgotten) in `before_fork`.
    unsafe { MAPPING.force_unlock() };
}

#[derive(Debug)]
pub enum PublishError {
    /// The backing memory region could not be allocated.
    Alloc,
    /// `madvise(MADV_DONTFORK)` failed.
    Madvise,
    /// The monotonic clock could not be read for the publish timestamp.
    Clock,
    /// `munmap` of the header mapping failed during unpublish.
    Munmap,
    /// `unpublish()` was called before any context was published.
    NotPublished,
}

impl From<PublishError> for PyErr {
    fn from(err: PublishError) -> Self {
        match err {
            PublishError::Alloc => {
                PyOSError::new_err("failed to allocate the process context mapping")
            }
            PublishError::Madvise => {
                PyOSError::new_err("madvise(MADV_DONTFORK) failed for the process context mapping")
            }
            PublishError::Clock => {
                PyOSError::new_err("failed to read the monotonic clock for the process context")
            }
            PublishError::Munmap => {
                PyOSError::new_err("munmap of the process context mapping failed")
            }
            PublishError::NotPublished => {
                PyRuntimeError::new_err("no process context has been published yet")
            }
        }
    }
}

/// Allocate the mapping and write the initial header. Called with the mutex held
/// and `guard` confirmed to be `None`.
fn publish_new(guard: &mut Option<Region>, payload: Vec<u8>) -> Result<(), PublishError> {
    let ptr = alloc_region()?;
    advise_dontfork(ptr, HEADER_SIZE)?;

    let timestamp = get_boottime_ns()?;

    // SAFETY: `ptr` points to a freshly mapped, zero initialized, page aligned
    // region of exactly `HEADER_SIZE` bytes. The payload lives in `payload` on
    // the heap and the header's `payload` field stores a pointer into it.
    unsafe {
        let header = ptr.as_ptr().cast::<Header>();

        std::ptr::addr_of_mut!((*header).signature).write(SIGNATURE);
        std::ptr::addr_of_mut!((*header).version).write(VERSION);
        std::ptr::addr_of_mut!((*header).payload_size).write(payload.len() as u32);
        std::ptr::addr_of_mut!((*header).payload).write(payload.as_ptr() as u64);

        // Write the timestamp last with release ordering, ensuring that
        // all writes above are not reordered after the timestamp store.
        let published_at = &*std::ptr::addr_of!((*header).monotonic_published_at_ns);
        published_at.store(timestamp, Ordering::Release);
    }

    // Best effort naming so readers can find the mapping even without a memfd
    // path, failures are ignored per the spec.
    name_mapping(ptr, HEADER_SIZE);

    *guard = Some(Region { ptr, payload });
    Ok(())
}

/// Rewrite the payload of an existing mapping in place. Called with the mutex
/// held and `region` confirmed to be live.
///
/// Follows the spec's Updating Protocol: zeros the timestamp to signal readers
/// that an update is in progress, rewrites the payload fields, then publishes
/// the new timestamp. The old payload buffer is dropped after the new timestamp
/// is live.
fn publish_existing(region: &mut Region, payload: Vec<u8>) -> Result<(), PublishError> {
    let timestamp = get_boottime_ns()?;

    // SAFETY: `region.ptr` points to the live header mapping with exactly
    // `HEADER_SIZE` bytes, writable for the process lifetime.
    unsafe {
        let header = region.ptr.as_ptr().cast::<Header>();
        let published_at = &*std::ptr::addr_of!((*header).monotonic_published_at_ns);

        // Zero timestamp signals the "update in progress" state.
        published_at.store(0, Ordering::Relaxed);
        // An `Ordering::Release` fence is needed here to ensure that the
        // preceding "update in progress" write above is not reordered with
        // any of the proceeding writes that update the region.
        std::sync::atomic::fence(Ordering::Release);

        // Rewrite payload fields between the two Release stores.
        std::ptr::addr_of_mut!((*header).payload_size).write(payload.len() as u32);
        std::ptr::addr_of_mut!((*header).payload).write(payload.as_ptr() as u64);

        // Publish new timestamp with Release ensuring the new payload fields
        // are visible to readers that observe the "update complete" signal.
        published_at.store(timestamp, Ordering::Release);
    }

    // Rename the mapping unconditionally (failures ignored per spec).
    name_mapping(region.ptr, HEADER_SIZE);

    // Drop the old payload only after the new timestamp is live.
    region.payload = payload;
    Ok(())
}

/// Publish or update the process context.
///
/// Creates the named memory mapping on the first call. On subsequent calls the
/// existing mapping is updated in-place using the spec's Updating Protocol
pub fn publish(payload: Vec<u8>) -> Result<(), PublishError> {
    let mut guard = MAPPING.lock();
    if let Some(region) = guard.as_mut() {
        publish_existing(region, payload)
    } else {
        publish_new(&mut guard, payload)
    }
}

/// Remove the published process context.
///
/// Zeros the timestamp (Release) so readers still observing the mapping see an
/// invalid state, then `munmap`s the header and drops the payload buffer.
/// After a successful call, `publish()` may be called again.
pub fn unpublish() -> Result<(), PublishError> {
    let mut guard = MAPPING.lock();
    let region = guard.take().ok_or(PublishError::NotPublished)?;

    // Zero the timestamp and remove the mapping.
    unsafe {
        let header = region.ptr.as_ptr().cast::<Header>();
        let published_at = &*std::ptr::addr_of!((*header).monotonic_published_at_ns);
        // No ordering constraint is required because regardless of ordering,
        // a reader can observe a valid timestamp before the store and subsequently
        // attempt to read from the header or payload pointer after it has already
        // deallocated/unmapped.
        published_at.store(0, Ordering::Relaxed);
    }

    unsafe { nix::sys::mman::munmap(region.ptr, HEADER_SIZE) }.map_err(|_| PublishError::Munmap)
}

/// Allocate the 32-byte header mapping: a `memfd`-backed mapping on Linux (so
/// it shows up in `/proc/<pid>/maps`), falling back to an anonymous mapping.
fn alloc_region() -> Result<NonNull<c_void>, PublishError> {
    let len = NonZeroUsize::new(HEADER_SIZE).unwrap();

    if let Some(ptr) = try_memfd_mapping(len) {
        return Ok(ptr);
    }

    // SAFETY: a fresh anonymous mapping with a valid, non-zero length.
    unsafe {
        mmap_anonymous(
            None,
            len,
            ProtFlags::PROT_READ | ProtFlags::PROT_WRITE,
            MapFlags::MAP_PRIVATE | MapFlags::MAP_ANONYMOUS,
        )
    }
    .map_err(|_| PublishError::Alloc)
}

/// Read the publish timestamp. Uses `CLOCK_BOOTTIME` on Linux (as the spec
/// requires) and `CLOCK_MONOTONIC` elsewhere. The value is forced non-zero, as a
/// zero timestamp is reserved to mean "being mutated, not ready".
fn get_boottime_ns() -> Result<u64, PublishError> {
    #[cfg(target_os = "linux")]
    let clock = ClockId::CLOCK_BOOTTIME;
    #[cfg(not(target_os = "linux"))]
    let clock = ClockId::CLOCK_MONOTONIC;

    let ts = clock_gettime(clock).map_err(|_| PublishError::Clock)?;
    let ns = (ts.tv_sec() as u64)
        .saturating_mul(1_000_000_000)
        .saturating_add(ts.tv_nsec() as u64);
    Ok(ns.max(1))
}

/// Prevent child processes from inheriting (stale) context memory.
#[cfg(target_os = "linux")]
fn advise_dontfork(ptr: NonNull<c_void>, len: usize) -> Result<(), PublishError> {
    // SAFETY: `ptr`/`len` describe the mapping we just created.
    unsafe { nix::sys::mman::madvise(ptr, len, nix::sys::mman::MmapAdvise::MADV_DONTFORK) }
        .map_err(|_| PublishError::Madvise)
}

#[cfg(not(target_os = "linux"))]
fn advise_dontfork(_ptr: NonNull<c_void>, _len: usize) -> Result<(), PublishError> {
    Ok(())
}

/// Create a `memfd`, size it, and map it `MAP_PRIVATE`. Returns `None` if any
/// step fails so the caller can fall back to an anonymous mapping.
#[cfg(target_os = "linux")]
fn try_memfd_mapping(len: NonZeroUsize) -> Option<NonNull<c_void>> {
    let base = MFdFlags::MFD_CLOEXEC | MFdFlags::MFD_ALLOW_SEALING;
    // `MFD_NOEXEC_SEAL` is a newer flag not exposed by `nix`, request it but
    // fall back without it on kernels/libc that lack it.
    let noexec_seal = MFdFlags::from_bits_retain(nix::libc::MFD_NOEXEC_SEAL as _);
    let fd = memfd_create(c"OTEL_CTX", base | noexec_seal)
        .or_else(|_| memfd_create(c"OTEL_CTX", base))
        .ok()?;

    nix::unistd::ftruncate(&fd, len.get() as nix::libc::off_t).ok()?;

    // SAFETY: `fd` is a valid, sized memfd and `len` is non-zero.
    let ptr = unsafe {
        mmap(
            None,
            len,
            ProtFlags::PROT_READ | ProtFlags::PROT_WRITE,
            MapFlags::MAP_PRIVATE,
            &fd,
            0,
        )
    }
    .ok()?;
    Some(ptr)
}

#[cfg(not(target_os = "linux"))]
fn try_memfd_mapping(_len: NonZeroUsize) -> Option<NonNull<c_void>> {
    None
}

/// Name the mapping `OTEL_CTX` via `prctl(PR_SET_VMA_ANON_NAME)`.
#[cfg(target_os = "linux")]
fn name_mapping(ptr: NonNull<c_void>, len: usize) {
    const NAME: &core::ffi::CStr = c"OTEL_CTX";
    unsafe {
        let _ = nix::libc::prctl(
            PR_SET_VMA,
            PR_SET_VMA_ANON_NAME,
            ptr.as_ptr() as nix::libc::c_ulong,
            len as nix::libc::c_ulong,
            NAME.as_ptr() as nix::libc::c_ulong,
        );
    }
}

#[cfg(not(target_os = "linux"))]
fn name_mapping(_ptr: NonNull<c_void>, _len: usize) {}

#[cfg(test)]
mod tests {
    use super::{PublishError, publish, unpublish};
    use serial_test::serial;

    #[test]
    fn get_boottime_ns_is_nonzero() {
        let ns = super::get_boottime_ns().unwrap();
        assert!(ns >= 1);
    }

    #[test]
    #[serial]
    fn unpublish_without_publish_returns_not_published() {
        let _ = unpublish();
        assert!(matches!(unpublish(), Err(PublishError::NotPublished)));
    }

    #[test]
    #[serial]
    fn publish_then_unpublish_succeeds() {
        let _ = unpublish();
        publish(b"test".to_vec()).unwrap();
        unpublish().unwrap();
    }

    #[test]
    #[serial]
    fn double_unpublish_returns_not_published() {
        let _ = unpublish();
        publish(b"test".to_vec()).unwrap();
        unpublish().unwrap();
        assert!(matches!(unpublish(), Err(PublishError::NotPublished)));
    }

    #[test]
    #[cfg(target_os = "linux")]
    fn try_memfd_mapping_returns_some() {
        use std::num::NonZeroUsize;
        let len = NonZeroUsize::new(32).unwrap();
        let ptr = super::try_memfd_mapping(len).expect("memfd_create + mmap should succeed");
        unsafe { nix::sys::mman::munmap(ptr, 32).unwrap() };
    }
}
