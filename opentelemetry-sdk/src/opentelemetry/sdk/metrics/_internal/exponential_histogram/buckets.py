# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Storage for the bucket counts of an exponential histogram.

One instance holds the counts of a single sign of a data point, so an
aggregation keeps two of them: one for the positive measurements and one
for the negative ones. The scale that turns a measured value into a bucket
index lives in the mapping classes under
``opentelemetry.sdk.metrics._internal.exponential_histogram.mapping``.
"""

from math import ceil, log2


class Buckets:
    """Counts of the buckets of one sign of an exponential histogram.

    The counts are held in a plain list that is read as a ring: position 0
    of the list holds the count of the bucket whose index is
    ``index_base``, and positions wrap around when the end of the list is
    reached. The rotation lets a measurement below the range recorded so
    far be written without moving the counts already stored. A caller that
    wants the counts in index order calls ``get_offset_counts``.

    An index identifies a bucket by its boundaries: the bucket with index
    ``i`` covers the values in ``(base ** i, base ** (i + 1)]``, where
    ``base`` comes from the scale of the mapping in use. Indexes are
    signed, so a value below 1 gets a negative index.

    No method here takes a lock. Every caller in
    ``opentelemetry.sdk.metrics._internal.aggregation`` already holds one.
    """

    def __init__(self):
        """Build an instance covering the single bucket with index 0.

        The backing list starts with one entry and ``index_base``,
        ``index_start`` and ``index_end`` all start at 0. ``__len__``
        reports 0 for that state, so an instance that has been offered
        nothing is indistinguishable from an empty histogram.
        """
        self._counts = [0]

        # The term index refers to the number of the exponential histogram bucket
        # used to determine its boundaries. The lower boundary of a bucket is
        # determined by base ** index and the upper boundary of a bucket is
        # determined by base ** (index + 1). index values are signedto account
        # for values less than or equal to 1.

        # self._index_* will all have values equal to a certain index that is
        # determined by the corresponding mapping _map_to_index function and
        # the value of the index depends on the value passed to _map_to_index.

        # Index of the 0th position in self._counts: self._counts[0] is the
        # count in the bucket with index self.__index_base.
        self.__index_base = 0

        # self.__index_start is the smallest index value represented in
        # self._counts.
        self.__index_start = 0

        # self.__index_start is the largest index value represented in
        # self._counts.
        self.__index_end = 0

    @property
    def index_start(self) -> int:
        """Return the smallest bucket index the counts cover.

        Returns:
            The index of the first bucket of the exported histogram. The
            aggregation lowers it when a measurement falls below the range
            recorded so far.
        """
        return self.__index_start

    @index_start.setter
    def index_start(self, value: int) -> None:
        """Move the lower end of the covered index range.

        The backing list is not resized here, so a caller that widens the
        range calls ``grow`` first when the range no longer fits.

        Args:
            value: The new smallest bucket index.
        """
        self.__index_start = value

    @property
    def index_end(self) -> int:
        """Return the largest bucket index the counts cover.

        Returns:
            The index of the last bucket of the exported histogram. The
            aggregation raises it when a measurement falls above the range
            recorded so far.
        """
        return self.__index_end

    @index_end.setter
    def index_end(self, value: int) -> None:
        """Move the upper end of the covered index range.

        The backing list is not resized here, so a caller that widens the
        range calls ``grow`` first when the range no longer fits.

        Args:
            value: The new largest bucket index.
        """
        self.__index_end = value

    @property
    def index_base(self) -> int:
        """Return the bucket index whose count sits at position 0.

        Returns:
            The index that position 0 of the backing list belongs to.
            ``downscale`` sets it equal to ``index_start``, which undoes
            the rotation.
        """
        return self.__index_base

    @index_base.setter
    def index_base(self, value: int) -> None:
        """Set the bucket index that position 0 of the backing list holds.

        Assigning here reinterprets the counts already stored rather than
        moving them, so the aggregation only assigns while the histogram
        is still empty.

        Args:
            value: The bucket index to give to position 0.
        """
        self.__index_base = value

    @property
    def counts(self):
        """Return the backing list of counts, by reference and uncopied.

        The order is the ring order described on the class, which is not
        the order the histogram is exported in. The aggregation reads the
        length of this list to decide whether a new index still fits, and
        calls ``get_offset_counts`` when it wants index order.

        Returns:
            The list holding the counts. Mutating it mutates the instance.
        """
        return self._counts

    def get_offset_counts(self):
        """Return the counts in index order, starting at ``index_start``.

        The ring rotation is undone, so position 0 of the result is the
        count of the bucket with index ``index_start``. This is the form
        an exporter writes into the ``bucket_counts`` field of a data
        point.

        Returns:
            A new list holding every entry of the backing list, rotated so
            that ``index_start`` comes first. Entries for indexes past
            ``index_end`` are included and are 0.
        """
        bias = self.__index_base - self.__index_start
        return self._counts[-bias:] + self._counts[:-bias]

    def grow(self, needed: int, max_size: int) -> None:
        """Enlarge the backing list, keeping the ring order intact.

        The new length is the smallest power of two that is at least
        ``needed``, held down to ``max_size`` when that power of two
        exceeds it. The entries are copied so that the zero padding lands
        between the counts of the high indexes and the counts of the low
        indexes, which is where the indexes that forced the growth will be
        written.

        ``index_start``, ``index_end`` and ``index_base`` are left as they
        were, so the caller widens the covered range itself afterwards.

        Args:
            needed: How many buckets have to fit once the call returns,
                counted across the whole range from ``index_start`` to
                ``index_end``.
            max_size: Upper bound on the length of the backing list, which
                comes from the ``max_size`` of the aggregation. When
                ``needed`` exceeds it the list is held at this length and
                the counts no longer span the requested range, so the
                caller downscales before reaching that point.
        """
        size = len(self._counts)
        bias = self.__index_base - self.__index_start
        old_positive_limit = size - bias

        # 2 ** ceil(log2(needed)) finds the smallest power of two that is larger
        # or equal than needed:
        # 2 ** ceil(log2(1)) == 1
        # 2 ** ceil(log2(2)) == 2
        # 2 ** ceil(log2(3)) == 4
        # 2 ** ceil(log2(4)) == 4
        # 2 ** ceil(log2(5)) == 8
        # 2 ** ceil(log2(6)) == 8
        # 2 ** ceil(log2(7)) == 8
        # 2 ** ceil(log2(8)) == 8
        new_size = min(2 ** ceil(log2(needed)), max_size)

        new_positive_limit = new_size - bias

        tmp = [0] * new_size
        tmp[new_positive_limit:] = self._counts[old_positive_limit:]
        tmp[0:old_positive_limit] = self._counts[0:old_positive_limit]
        self._counts = tmp

    @property
    def offset(self) -> int:
        """Return the index of the first bucket of the exported histogram.

        This is the same value as ``index_start``, under the name the
        OpenTelemetry data model gives the field.

        Returns:
            The bucket index that position 0 of ``get_offset_counts``
            belongs to.
        """
        return self.__index_start

    def __len__(self) -> int:
        """Return how many buckets the covered index range spans.

        Returns:
            ``index_end - index_start + 1``. The result is 0 when the
            backing list is empty, and 0 when the range is a single bucket
            whose count is still 0, which is the state a fresh instance
            starts in. The length of the backing list is usually larger,
            since it is sized in powers of two.
        """
        if len(self._counts) == 0:
            return 0

        if self.__index_end == self.__index_start and self[0] == 0:
            return 0

        return self.__index_end - self.__index_start + 1

    def __getitem__(self, key: int) -> int:
        """Return the count of one bucket, addressed in index order.

        Args:
            key: Position counted from ``index_start``, so 0 is the bucket
                with index ``index_start``. The ring rotation is undone
                here, so this is the same position ``get_offset_counts``
                uses.

        Returns:
            The count of that bucket.

        Raises:
            IndexError: If ``key`` is large enough that the position it
                translates to falls past the end of the backing list.
        """
        bias = self.__index_base - self.__index_start

        if key < bias:
            key += len(self._counts)

        key -= bias

        return self._counts[key]

    def downscale(self, amount: int) -> None:
        """
        Rotates, then collapses 2 ** amount to 1 buckets.

        The rotation puts the count of ``index_start`` back at position 0
        of the backing list, which makes ``index_base`` equal to
        ``index_start`` again. Each run of ``2 ** amount`` neighbouring
        buckets is then summed into the leftmost position of the run and
        the positions it was read from are set to 0. Runs are aligned on
        multiples of ``2 ** amount`` in index space, which is what keeps
        the result equal to what a mapping of the lower scale would have
        produced from the same measurements.

        ``index_start`` and ``index_end`` are right shifted by ``amount``
        afterwards, and ``index_base`` is set to ``index_start``. The
        backing list keeps its length, with the positions above the new
        range left at 0.

        Args:
            amount: How many steps the scale drops by. Each step merges
                two neighbouring buckets into one, so an ``amount`` of 0
                rotates and changes nothing else.
        """

        bias = self.__index_base - self.__index_start

        if bias != 0:
            self.__index_base = self.__index_start

            # [0, 1, 2, 3, 4] Original backing array

            self._counts = self._counts[::-1]
            # [4, 3, 2, 1, 0]

            self._counts = self._counts[:bias][::-1] + self._counts[bias:][::-1]
            # [3, 4, 0, 1, 2] This is a rotation of the backing array.

        size = 1 + self.__index_end - self.__index_start
        each = 1 << amount
        inpos = 0
        outpos = 0

        pos = self.__index_start

        while pos <= self.__index_end:
            mod = pos % each
            if mod < 0:
                mod += each

            index = mod

            while index < each and inpos < size:
                if outpos != inpos:
                    self._counts[outpos] += self._counts[inpos]
                    self._counts[inpos] = 0

                inpos += 1
                pos += 1
                index += 1

            outpos += 1

        self.__index_start >>= amount
        self.__index_end >>= amount
        self.__index_base = self.__index_start

    def increment_bucket(self, bucket_index: int, increment: int = 1) -> None:
        """Add to the count held at one position of the backing list.

        The position is used as given. Unlike ``__getitem__`` this does
        not translate from index order, so the caller subtracts
        ``index_base`` from the bucket index and wraps the result into the
        length of the backing list first.

        Args:
            bucket_index: Position in the backing list, which is the
                bucket index minus ``index_base``, wrapped around the
                length of the list.
            increment: How much to add. Recording a measurement adds 1;
                merging a previous data point into the current one passes
                the count being merged.
        """
        self._counts[bucket_index] += increment

    def copy_empty(self) -> "Buckets":
        """Return a new instance with this index range and no counts.

        The three index attributes are copied and the backing list of the
        copy has the same length as this one, with every entry 0. Delta
        temporality uses this to start a collection cycle already laid out
        the way the previous one ended, so that adding the copy to the
        current counts leaves them unchanged.

        Returns:
            A new ``Buckets`` that shares no list with this one.
        """
        copy = Buckets()

        # pylint: disable=no-member
        # pylint: disable=protected-access
        # pylint: disable=attribute-defined-outside-init
        # pylint: disable=invalid-name
        copy._Buckets__index_base = self._Buckets__index_base  # type: ignore[reportArgumentType]
        copy._Buckets__index_start = self._Buckets__index_start  # type: ignore[reportArgumentType]
        copy._Buckets__index_end = self._Buckets__index_end  # type: ignore[reportArgumentType]
        copy._counts = [0 for _ in self._counts]

        return copy
