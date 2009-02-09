import unittest
import pitivi
from pitivi.application import Pitivi
from pitivi.utils import binary_search

class BasicTest(unittest.TestCase):
    """
    Basic test to create the proper creation of the Pitivi object
    """

    def testBinarySearch(self):
        # binary_search always returns an index, so we do the comparison here
        def found(A, result, value):
            if ((result < len(A)) and (A[result] == value)):
                return result
            else:
                return False

        for offset in xrange(1, 5):
            for length in xrange(1, 2049, 300):
                A = [i * offset for i in xrange(0, length)]
                
## check negative hits
 
                # search value too low
                # error if value is found
                # if search returns non-negative index, fail
                value = A[0] - 1
                self.assertFalse(found(A, binary_search(A, value), value))
 
                # search value too high
                # error if value is found
                # if search returns non-negative index, fail
                value = A[-1] + 1
                self.assertFalse(found(A, binary_search(A, value), value))
 
## check positive hits
                for i, a in enumerate(A):
                    # error if value is NOT found
                    # if search does not return correct value, fail
                    self.assertEquals(binary_search(A, A[i]), i)

if __name__ == "__main__":
    unittest.main()
