// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

//! Publication of the process context to a memory region that out-of-process
//! readers (e.g. the OpenTelemetry eBPF Profiler) can discover and read.
//!
//! The layout follows the OpenTelemetry "Process Context" specification: a fixed
//! 32-byte header mapping named `OTEL_CTX` and backed by a `memfd` on Linux
//! (visible in `/proc/<pid>/maps`), with the payload living out-of-band in a
//! heap-allocated buffer. This means the header mapping never needs resizing:
//! updates only swap the payload buffer and rewrite the header pointer fields.

use std::ffi::c_void;
use std::num::NonZeroUsize;
use std::ptr::NonNull;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;

use nix::sys::mman::{mmap_anonymous, MapFlags, ProtFlags};
use nix::time::{clock_gettime, ClockId};
use pyo3::exceptions::{PyOSError, PyRuntimeError};
use pyo3::PyErr;

/// 8 byte signature stamped at the start of the header.
const SIGNATURE: [u8; 8] = *b"OTEL_CTX";
/// Format version. `2` is the first stable version (`1` is for development).
const VERSION: u32 = 2;
/// Size of the header mapping in bytes. The payload lives on the heap.
const HEADER_SIZE: usize = 32;

/// The process context header.
#[repr(C)]
struct Header {
    signature: [u8; 8],
    version: u32,
    payload_size: u32,
    monotonic_published_at_ns: AtomicU64,
    payload: u64,
}

const _: () = assert!(std::mem::size_of::<Header>() == HEADER_SIZE);

/// A published mapping.
#[allow(dead_code)]
struct Region {
    ptr: NonNull<c_void>,
    payload: Vec<u8>,
}

// SAFETY: all access goes through `MAPPING` (a `Mutex`), which serializes
// reads and writes. The pointer lives for the process lifetime.
unsafe impl Send for Region {}

/// The single active process context for this process, if any.
static MAPPING: Mutex<Option<Region>> = Mutex::new(None);

#[derive(Debug)]
pub enum PublishError {
    /// A process context has already been published for this process.
    AlreadyPublished,
    /// `update()` was called before any context was published.
    NotPublished,
    /// The backing memory region could not be allocated.
    Alloc,
    /// `madvise(MADV_DONTFORK)` failed.
    Madvise,
    /// The monotonic clock could not be read for the publish timestamp.
    Clock,
    /// `munmap` of the header mapping failed during unpublish.
    Munmap,
}

impl From<PublishError> for PyErr {
    fn from(err: PublishError) -> Self {
        match err {
            PublishError::AlreadyPublished => {
                PyRuntimeError::new_err("a process context has already been published")
            }
            PublishError::NotPublished => {
                PyRuntimeError::new_err("no process context has been published yet")
            }
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
        }
    }
}

/// Publish `payload` as the process context.
///
/// The context is a per-process singleton: calling this a second time without a
/// prior teardown returns [`PublishError::AlreadyPublished`].
pub fn publish(payload: Vec<u8>) -> Result<(), PublishError> {
    let mut guard = MAPPING.lock().expect("process context mutex poisoned");
    if guard.is_some() {
        return Err(PublishError::AlreadyPublished);
    }

    let ptr = alloc_region()?;
    advise_dontfork(ptr, HEADER_SIZE)?;

    let timestamp = get_boottime_ns()?;

    let payload_buf = payload;

    // SAFETY: `ptr` points to a freshly mapped, zero initialized, page aligned
    // region of exactly `HEADER_SIZE` bytes. The payload lives in `payload_buf`
    // on the heap and the header's `payload` field stores a pointer into it.
    unsafe {
        let header = ptr.as_ptr().cast::<Header>();

        std::ptr::addr_of_mut!((*header).signature).write(SIGNATURE);
        std::ptr::addr_of_mut!((*header).version).write(VERSION);
        std::ptr::addr_of_mut!((*header).payload_size).write(payload_buf.len() as u32);
        std::ptr::addr_of_mut!((*header).payload).write(payload_buf.as_ptr() as u64);

        // Write the timestamp last with release ordering.
        let published_at = &*std::ptr::addr_of!((*header).monotonic_published_at_ns);
        published_at.store(timestamp, Ordering::Release);
    }

    // Best effort naming so readers can find the mapping even without a memfd
    // path, failures are ignored per the spec.
    name_mapping(ptr, HEADER_SIZE);

    *guard = Some(Region { ptr, payload: payload_buf });
    Ok(())
}

/// Update the published process context with a new payload.
///
/// Follows the spec's Updating Protocol: zeros the timestamp (Release) to signal
/// readers that an update is in progress, rewrites the payload fields and then
/// publishes the new timestamp (Release) to signal completion. The old payload
/// buffer is dropped after the new timestamp is live.
pub fn update(payload: Vec<u8>) -> Result<(), PublishError> {
    let mut guard = MAPPING.lock().expect("process context mutex poisoned");
    let region = guard.as_mut().ok_or(PublishError::NotPublished)?;

    let new_buf = payload;
    let timestamp = get_boottime_ns()?;

    // SAFETY: `region.ptr` points to the live header mapping with exactly
    // `HEADER_SIZE` bytes, writable for the process lifetime.
    unsafe {
        let header = region.ptr.as_ptr().cast::<Header>();
        let published_at = &*std::ptr::addr_of!((*header).monotonic_published_at_ns);

        // Zero timestamp with Release ensuring the previous payload state is
        // visible to readers that observe the "update in progress" signal.
        published_at.store(0, Ordering::Relaxed);
        std::sync::atomic::fence(Ordering::Release);

        // Rewrite payload fields between the two Release stores.
        std::ptr::addr_of_mut!((*header).payload_size).write(new_buf.len() as u32);
        std::ptr::addr_of_mut!((*header).payload).write(new_buf.as_ptr() as u64);

        // Publish new timestamp with Release ensuring the new payload fields
        // are visible to readers that observe the "update complete" signal.
        published_at.store(timestamp, Ordering::Release);
    }

    // Rename the mapping unconditionally (failures ignored per spec).
    name_mapping(region.ptr, HEADER_SIZE);

    // Drop the old payload only after the new timestamp is live
    region.payload = new_buf;
    Ok(())
}

/// Remove the published process context.
///
/// Zeros the timestamp (Release) so readers still observing the mapping see an
/// invalid state, then `munmap`s the header and drops the payload buffer.
/// After a successful call, `publish()` may be called again.
pub fn unpublish() -> Result<(), PublishError> {
    let mut guard = MAPPING.lock().expect("process context mutex poisoned");
    let region = guard.take().ok_or(PublishError::NotPublished)?;

    // Zero the timestamp with Release before removing the mapping so any
    // reader still observing it sees an invalid (zero) state.
    unsafe {
        let header = region.ptr.as_ptr().cast::<Header>();
        let published_at = &*std::ptr::addr_of!((*header).monotonic_published_at_ns);
        published_at.store(0, Ordering::Release);
    }

    unsafe { nix::sys::mman::munmap(region.ptr, HEADER_SIZE) }
        .map_err(|_| PublishError::Munmap)
}

/// Allocate the 32-byte header mapping: a `memfd`-backed mapping on Linux (so
/// it shows up in `/proc/<pid>/maps`), falling back to an anonymous mapping.
fn alloc_region() -> Result<NonNull<c_void>, PublishError> {
    let len = NonZeroUsize::new(HEADER_SIZE).unwrap();

    #[cfg(target_os = "linux")]
    if let Some(ptr) = linux::try_memfd_mapping(len) {
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

/// Name the mapping `OTEL_CTX` via `prctl(PR_SET_VMA_ANON_NAME)`.
#[cfg(target_os = "linux")]
fn name_mapping(ptr: NonNull<c_void>, len: usize) {
    linux::name_mapping(ptr, len);
}

#[cfg(not(target_os = "linux"))]
fn name_mapping(_ptr: NonNull<c_void>, _len: usize) {}

#[cfg(target_os = "linux")]
mod linux {
    use std::ffi::c_void;
    use std::num::NonZeroUsize;
    use std::ptr::NonNull;

    use nix::sys::memfd::{memfd_create, MFdFlags};
    use nix::sys::mman::{mmap, MapFlags, ProtFlags};

    // `prctl` options for naming an anonymous VMA.
    const PR_SET_VMA: nix::libc::c_int = 0x53564d41;
    const PR_SET_VMA_ANON_NAME: nix::libc::c_ulong = 0;

    /// Create a `memfd`, size it, and map it `MAP_PRIVATE`. Returns `None` if any
    /// step fails so the caller can fall back to an anonymous mapping.
    pub(super) fn try_memfd_mapping(len: NonZeroUsize) -> Option<NonNull<c_void>> {
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

    pub(super) fn name_mapping(ptr: NonNull<c_void>, len: usize) {
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
}
