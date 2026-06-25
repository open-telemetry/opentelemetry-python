// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

use std::ffi::c_void;
use std::num::NonZeroUsize;
use std::ptr::NonNull;

use nix::sys::memfd::{MFdFlags, memfd_create};
use nix::sys::mman::{MapFlags, ProtFlags, mmap};

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
