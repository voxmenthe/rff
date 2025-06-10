from reason_from_future.core import reason_from_future
from reason_from_future.specs import Game24Spec

easy = [1, 3, 6, 11] # (11-3) * (6-3) == 24
easy_2 = [1, 2, 5, 9]  # 1, 2, 5, 9 ==> (9-1) * (5-2) ==> 8 * 3 == 24 // or (9 * 2) + 5 + 1 == 24
hard = [2, 3, 5, 12] # (12/(3-(5/2))) == 24 - takes o3 to solve it

current = easy_2

# Example: reach 24
spec = Game24Spec(current)
answer = reason_from_future("Reach 24 with all the numbers {}".format(current), spec, verbose=True)
print("Solution:", answer)