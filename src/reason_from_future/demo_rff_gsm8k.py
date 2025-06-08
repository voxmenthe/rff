from reason_from_future.core import reason_from_future
from reason_from_future.specs.gsm8k import GSM8KSpec

simple_sample = {
    "question": "There were 15 trees in the grove. 3 were cut down. Then, after some time, 2 more were cut down. But 1 grew back. How many are left?",
    "answer": "11",
}

harder_sample = {
    "question": """A school library ordered 600 new books for three sections: Fiction, Science, and History. Exactly half of the order was Fiction. The remaining books were split equally between Science and History.
    During shipping the library discovered that
    10 percent of the Fiction books and 10 percent of the Science books were damaged, and
    15 History books were lost.

    The library reordered one replacement copy for every damaged or lost book.
    As a thank-you, the supplier added bonus copies equal to 20 percent of the total number of replacements, and all of these bonus copies were Science books.

    After the replacements and bonus copies arrived, how many Science books did the library have in total?""",
    "answer": "200", # actually 162 - putting 200 temporarily to get it to iterate more - TODO: fix so it doesn't depend on having right answer here
}

CURRENT_SAMPLE = harder_sample

def main(verbose=True):
    spec = GSM8KSpec(CURRENT_SAMPLE)
    answer = reason_from_future(
        problem=CURRENT_SAMPLE["question"],
        spec=spec,
        max_iters=8,
        verbose=verbose,
    )
    print("FINAL ANSWER:", answer)

if __name__ == "__main__":
    main()