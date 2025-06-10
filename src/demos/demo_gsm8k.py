from reason_from_future.core import reason_from_future
from reason_from_future.specs.gsm8k import GSM8KSpec

simple = {
    "question": "There were 15 trees in the grove. 3 were cut down. Then, after some time, 2 more were cut down. But 1 grew back. How many are left?",
    "answer": "11",
}

medium = {
    "question": """A school library ordered 600 new books for three new sections: Fiction, Science, and History. Exactly half of the order was Fiction. The remaining books were split equally between Science and History.
    During shipping the library discovered that
    10 percent of the Fiction books and 10 percent of the Science books were damaged, and
    15 History books were lost.

    The library reordered one replacement copy for every damaged or lost book.
    As a thank-you, the supplier added bonus copies equal to 40 percent of the total number of replacements, and half of these bonus copies were Science books.
    
    Then, the library received a donation of science books equal to 50 percent of the number of Science books it already had, but 5/9 of those were stolen.

    After the replacements and bonus copies arrived, how many Science books did the library have in total?""",
    "answer": "198", 
}

medium_2 = {
    "question": """If the sum of the smallest and largest of five consecutive even numbers is 76, what is the value of the second largest number in the series added to the smallest number in the series?""",
    "answer": "74"
}


CURRENT_SAMPLE = medium_2

def main(verbose=True):
    spec = GSM8KSpec(CURRENT_SAMPLE)
    answer = reason_from_future(
        problem=CURRENT_SAMPLE["question"],
        spec=spec,
        max_iters=7,
        verbose=verbose,
        require_gold=False,
        min_iters=2,
    )
    print("FINAL ANSWER:", answer)

if __name__ == "__main__":
    main()