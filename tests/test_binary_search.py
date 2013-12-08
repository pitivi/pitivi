import unittest
from pitivi.utils.misc import binary_search
from common import TestCase


class BinarySearchTest(TestCase):

    def testEmptyList(self):
        self.assertEquals(binary_search([], 10), -1)

    def testExisting(self):
        A = [10, 20, 30]
        for index, element in enumerate(A):
            self.assertEquals(binary_search([10, 20, 30], element), index)

    def testMissingLeft(self):
        self.assertEquals(binary_search([10, 20, 30], 1), 0)
        self.assertEquals(binary_search([10, 20, 30], 16), 1)
        self.assertEquals(binary_search([10, 20, 30], 29), 2)

    def testMissingRight(self):
        self.assertEquals(binary_search([10, 20, 30], 11), 0)
        self.assertEquals(binary_search([10, 20, 30], 24), 1)
        self.assertEquals(binary_search([10, 20, 30], 40), 2)


if __name__ == "__main__":
    unittest.main()
