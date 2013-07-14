"""Copyright (c) 2012 Nezar Abdennur

This module contains code from the Python implementation of the heapq module,
which was written by Kevin O'Connor and augmented by Tim Peters and Raymond
Hettinger.

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to
    deal in the Software without restriction, including without limitation the
    rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    sell copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
    IN THE SOFTWARE.

"""

"""Priority Queue Dictionary -- An indexed priority queue data structure.

Stores a set of prioritized hashable items. Useful as an updatable schedule.

The priority queue is implemented as a binary heap, which supports:    
    - O(1) access to the top priority item     
    - O(log n) deletion of the top priority item
    - O(log n) insertion of a new item

In addition, an internal dictionary or "index" maps items to their position in
the heap array. This index is kept up-to-date when the heap is manipulated. As a
result, PQD also supports:     
    - O(1) lookup of an arbitrary item's priority key
    - O(log n) deletion of an arbitrary item     
    - O(log n) updating of an arbitrary item's priority key

The standard heap operations used internally (here, called "sink" and "swim")
are based on the code in the python heapq module.* These operations are extended
to preserve correctness of the internal dictionary.

* The names of the methods in heapq (sift up/down) seem to refer to the motion
of the items being compared to, rather than the item being operated on as is
normally done in textbooks (i.e. bubble down/up, instead). I stuck to the
textbook convention, but using the sink/swim nomenclature from Sedgewick et al:
the way I see it, an item that is too "heavy" (low-priority) should sink down
the tree, while one that is too "light" should float or swim up. Note, however,
that the sink implementation is non-conventional. See heapq for details about
why.

""" 
__author__ = ('Nezar Abdennur', 'nabdennur@gmail.com') 
__license__ = 'MIT'
__all__ = ['PQDict', 'PQDictEntry']

from collections import Mapping, MutableMapping
from abc import ABCMeta, abstractmethod

class PQDictEntry(object):
    __metaclass__ = ABCMeta
    def __init__(self, dkey, pkey):
        self.dkey = dkey
        self.pkey = pkey

    @abstractmethod
    def __lt__(self, other):
        return NotImplemented

    # def set_pkey(self, pkey):
    #     pass

    def __eq__(self, other):
        return self.pkey == other.pkey

    def __repr__(self):
        return self.__class__.__name__ + \
            "(%s: %s)" % (repr(self.dkey), self.pkey)

class MinPQDEntry(PQDictEntry):
    __init__ = PQDictEntry.__init__
    __eq__ = PQDictEntry.__eq__

    def __lt__(self, other):
        return self.pkey < other.pkey

class MaxPQDEntry(PQDictEntry):
    __init__ = PQDictEntry.__init__
    __eq__ = PQDictEntry.__eq__

    def __lt__(self, other):
        return self.pkey > other.pkey


class PQDict(MutableMapping):
    """
    Maps dictionary keys (keys) to priority keys (values). Maintains an
    internal heap so that the highest priority item can always be obtained in
    constant time. The mapping is mutable so items may be added, removed and
    have their priorities updated.

    """
    # Implementation details:
    #   - heap (list): stores (dkey,pkey)-pairs as "entries" (PQDEntry objects).
    #   - nodefinder (dict): maps each dkey to the position of its entry in the 
    #     heap
    #   - the < comparator is used to rank entries
    __slots__ = ('nodefinder', 'heap', 'create_entry')
    create_entry = MinPQDEntry

    __eq__ = MutableMapping.__eq__
    __ne__ = MutableMapping.__ne__
    keys = MutableMapping.keys
    values = MutableMapping.values
    items = MutableMapping.items
    get = MutableMapping.get
    clear = MutableMapping.clear
    update = MutableMapping.update
    setdefault = MutableMapping.setdefault
    #fromkeys

    def __init__(self, *args, **kwargs):
        """
        Mimics the standard dict constructor:
            Accepts a sequence/iterator of (dkey, pkey) pairs.
            Accepts named arguments or an unpacked dictionary.
        Also accepts a single mapping object to convert it to a pqdict.

        The default priority ranking for entries is in decreasing pkey value
        (i.e., a min-pq: LOWER pkey values have a HIGHER rank). This is typical
        for a scheduler, where the higher ranked tasks have earlier times.

        """
        if len(args) > 1:
            raise TypeError

        self.heap = []
        self.nodefinder = {}
        pos = 0
        if args:
            if isinstance(args[0], Mapping):
                seq = args[0].items()
            else:
                seq = args[0]
            try:
                for dkey, pkey in seq:
                    entry = self.create_entry(dkey, pkey)
                    self.heap.append(entry)
                    self.nodefinder[dkey] = pos
                    pos += 1
            except TypeError:
                raise ValueError
        if kwargs:
            for dkey, pkey in kwargs.items():
                entry = self.create_entry(dkey, pkey)
                self.heap.append(entry)
                self.nodefinder[dkey] = pos
                pos += 1
        self._heapify()

    @classmethod
    def minpq(cls, *args, **kwargs):
        pq = cls()
        pq.create_entry = MinPQDEntry
        pq.__init__(*args, **kwargs)
        return pq

    @classmethod
    def maxpq(cls, *args, **kwargs):
        pq = cls()
        pq.create_entry = MaxPQDEntry
        pq.__init__(*args, **kwargs)
        return pq

    @classmethod
    def custompq(cls, entrytype, *args, **kwargs):
        pq = cls()
        if issubclass(entrytype, PQDictEntry):
            pq.create_entry = entrytype
        else:
            raise TypeError('Custom entry class must be a subclass of' \
                            'PQDictEntry')
        pq.__init__(*args, **kwargs)
        return pq

    @classmethod
    def fromfunction(cls, iterable, pkeygen): #instead of fromkeys
        """
        Provide a key function that determines priorities by which to heapify
        the elements of an iterable into a PQD.

        """
        return cls( (dkey, pkeygen(dkey)) for dkey in iterable )

    def __len__(self):
        """
        Return number of items in the PQD.

        """
        return len(self.nodefinder)

    def __contains__(self, dkey):
        """
        Return True if dkey is in the PQD else return False.

        """
        return dkey in self.nodefinder

    def __iter__(self):
        """
        Return an iterator over the dictionary keys of the PQD.

        """
        for entry in self.heap:
            yield entry.dkey

    def __getitem__(self, dkey):
        """
        Return the priority of dkey. Raises a KeyError if not in the PQD.

        """
        return self.heap[self.nodefinder[dkey]].pkey #raises KeyError

    def __setitem__(self, dkey, pkey):
        """
        Assign priority to dictionary key.

        """
        heap = self.heap
        finder = self.nodefinder
        try:
            pos = finder[dkey]
        except KeyError:
            # add new entry
            n = len(self.heap)
            self.heap.append(self.create_entry(dkey, pkey))
            self.nodefinder[dkey] = n
            self._swim(n)
        else:
            # update existing entry
            heap[pos].pkey = pkey
            parent_pos = (pos - 1) >> 1
            child_pos = 2*pos + 1
            if parent_pos > 0 and heap[pos] < heap[parent_pos]:
                self._swim(pos)
            elif child_pos < len(heap):
                right_pos = child_pos + 1
                if (right_pos < len(heap) 
                        and not heap[child_pos] < heap[right_pos]):
                    child_pos = right_pos
                if heap[child_pos] < heap[pos]:
                    self._sink(pos)

    def __delitem__(self, dkey):
        """
        Remove item. Raises a KeyError if dkey is not in the PQD.

        """
        heap = self.heap
        finder = self.nodefinder

        # Remove very last item and place in vacant spot. Let the new item
        # sink until it reaches its new resting place.
        try:
            pos = finder.pop(dkey)
        except KeyError:
            raise
        else:
            entry = heap[pos]
            last = heap.pop(-1)
            if entry is not last:
                heap[pos] = last
                finder[last.dkey] = pos
                parent_pos = (pos - 1) >> 1
                child_pos = 2*pos + 1
                if parent_pos > 0 and heap[pos] < heap[parent_pos]:
                    self._swim(pos)
                elif child_pos < len(heap):
                    right_pos = child_pos + 1
                    if (right_pos < len(heap) 
                            and not heap[child_pos] < heap[right_pos]):
                        child_pos = right_pos
                    if heap[child_pos] < heap[pos]:
                        self._sink(pos)
            del entry

    def __copy__(self):
        """
        Return a new PQD with the same dkeys associated with the same priority
        keys.

        """
        # We want the two PQDs to behave as different schedules on the same
        # set of dkeys. As a result:
        #   - The new heap list contains copies of all entries because PQDEntry
        #     objects are mutable and should not be shared by two PQDicts.
        #   - The new nodefinder dict (dkey->heap positions) must be a copy of 
        #     the old nodefinder dict since it maps the same dkeys to positions 
        #     in a different list.
        from copy import copy
        other = self.__class__()
        other.heap = [copy(entry) for entry in self.heap]
        other.nodefinder = copy(self.nodefinder)
        return other
    copy = __copy__

    def __repr__(self):
        things = ', '.join(['%s: %s' % (repr(entry.dkey), entry.pkey) 
                                for entry in self.heap])
        return self.__class__.__name__ + '({' + things  + '})'

    __marker = object()
    def pop(self, dkey, default=__marker):
        """
        If dkey is in the PQD, remove it and return its priority key, else 
        return default. If default is not given and dkey is not in the PQD, a 
        KeyError is raised.

        """
        heap = self.heap
        finder = self.nodefinder

        try:
            pos = finder.pop(dkey)
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            delentry = heap[pos]
            last = heap.pop(-1)
            if delentry is not last:
                heap[pos] = last
                finder[last.dkey] = pos
                parent_pos = (pos - 1) >> 1
                child_pos = 2*pos + 1
                if parent_pos > 0 and heap[pos] < heap[parent_pos]:
                    self._swim(pos)
                elif child_pos < len(heap):
                    right_pos = child_pos + 1
                    if (right_pos < len(heap) 
                            and not heap[child_pos] < heap[right_pos]):
                        child_pos = right_pos
                    if heap[child_pos] < heap[pos]:
                        self._sink(pos)
            pkey = delentry.pkey
            del delentry
            return pkey

    def popitem(self):
        """
        Extract top priority item. Raises KeyError if PQD is empty.

        """
        try:
            last = self.heap.pop(-1)
        except IndexError:
            raise KeyError
        else:
            if self.heap:
                entry = self.heap[0]
                self.heap[0] = last
                self.nodefinder[last.dkey] = 0
                self._sink(0)
            else:
                entry = last
            self.nodefinder.pop(entry.dkey)
            return entry.dkey, entry.pkey

    def additem(self, dkey, pkey):
        """
        Add a new item. Raises KeyError if item is already in the PQD.

        """
        if dkey in self.nodefinder:
            raise KeyError
        self[dkey] = pkey

    def updateitem(self, dkey, new_pkey):
        """
        Update the priority key of an existing item. Raises KeyError if item is
        not in the PQD.

        """
        if dkey not in self.nodefinder:
            raise KeyError
        self[dkey] = new_pkey

    def peek(self):
        """
        Get top priority item.

        """
        try:
            entry = self.heap[0]
        except IndexError:
            raise KeyError
        return entry.dkey, entry.pkey

    def _heapify(self):
        n = len(self.heap)
        for pos in reversed(range(n//2)):
            self._sink(pos)

    def _sink(self, top=0):
        heap = self.heap
        finder = self.nodefinder

        # Peel off top item
        pos = top
        entry = heap[pos]

        # Sift up a trail of child nodes
        child_pos = 2*pos + 1
        while child_pos < len(heap):
            # Choose the index of smaller child.
            right_pos = child_pos + 1
            if right_pos < len(heap) and not heap[child_pos] < heap[right_pos]:
                child_pos = right_pos

            # Move the smaller child up.
            child_entry = heap[child_pos]
            heap[pos] = child_entry
            finder[child_entry.dkey] = pos

            pos = child_pos
            child_pos = 2*pos + 1

        # We are now at a leaf. Put item there and let it swim until it reaches
        # its new resting place.
        heap[pos] = entry
        finder[entry.dkey] = pos
        self._swim(pos, top)

    def _swim(self, pos, top=0):
        heap = self.heap
        finder = self.nodefinder

        # Remove item from its place
        entry = heap[pos]

        # Bubble item up by sifting parents down until finding a place it fits.
        while pos > top:
            parent_pos = (pos - 1) >> 1
            parent_entry = heap[parent_pos]
            if entry < parent_entry:
                heap[pos] = parent_entry
                finder[parent_entry.dkey] = pos
                pos = parent_pos
                continue
            break

        # Put item in its new place
        heap[pos] = entry
        finder[entry.dkey] = pos