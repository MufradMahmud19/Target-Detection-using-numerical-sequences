"""
Fibonacci Series Movement Module
X-axis: Fibonacci sequence (1, 1, 2, 3, 5, 8, 13, 21, ...)
Y-axis: Linear sequence (1, 2, 3, 4, 5, ...)
On wall hit: the corresponding sequence resets to the beginning.
"""

SERIES_NAME = "Fibonacci Series"
SERIES_KEY = "fibonacci"
SERIES_DESCRIPTION = "X: Fibonacci (1,1,2,3,5,8,...)  |  Y: Linear (1,2,3,...)"

class SeriesMovement:
    """Movement logic where X follows the Fibonacci sequence and Y increases linearly."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all sequence state to initial values."""
        self.fib_prev = 0
        self.fib_curr = 1
        self.linear_step = 0
        self.last_x_step = 0
        self.last_y_step = 0

    def get_next_step(self):
        """
        Advance sequences and return the next step sizes.
        Returns:
            (x_step, y_step): raw integer step values before direction/scale.
        """
        # Fibonacci for X: yields 1, 1, 2, 3, 5, 8, 13, ...
        self.fib_prev, self.fib_curr = self.fib_curr, self.fib_prev + self.fib_curr
        self.last_x_step = self.fib_prev

        # Linear for Y: yields 1, 2, 3, 4, 5, ...
        self.linear_step += 1
        self.last_y_step = self.linear_step

        return self.last_x_step, self.last_y_step

    def on_x_wall_hit(self):
        """Reset X (Fibonacci) sequence when the searcher hits a left/right wall."""
        self.fib_prev = 0
        self.fib_curr = 1

    def on_y_wall_hit(self):
        """Reset Y (Linear) sequence when the searcher hits a top/bottom wall."""
        self.linear_step = 0

    def get_x_label(self):
        """Short label for X movement info in the HUD."""
        return "Fib X: {}".format(self.last_x_step)

    def get_y_label(self):
        """Short label for Y movement info in the HUD."""
        return "Lin Y: {}".format(self.last_y_step)

    def get_sequence_preview(self):
        """Return a string showing the sequence pattern for display."""
        # Generate first 12 fibonacci numbers for preview
        a, b = 0, 1
        fib_seq = []
        for _ in range(12):
            a, b = b, a + b
            fib_seq.append(str(a))
        return "X seq: " + ",".join(fib_seq) + ",...  |  Y seq: 1,2,3,4,5,..."
