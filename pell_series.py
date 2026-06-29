"""
Pell Series Movement Module
X-axis: Pell numbers (1, 2, 5, 12, 29, 70, 169, ...)
Y-axis: Linear sequence (1, 2, 3, 4, 5, ...)

The Rule:
  Each term is the sum of TWICE the preceding term and the term
  before that:  P(n) = 2*P(n-1) + P(n-2)

  Starting values: P(0)=0, P(1)=1  (we skip the leading 0)

The Connection:
  The ratio of consecutive Pell numbers converges to the
  Silver Ratio (1 + sqrt(2) ~ 2.414). This makes Pell numbers
  grow significantly faster than Fibonacci, producing aggressive
  wall-bouncing behaviour.

On wall hit: the corresponding sequence resets to the beginning.
"""

SERIES_NAME = "Pell Series"
SERIES_KEY = "pell"
SERIES_DESCRIPTION = "X: Pell (1,2,5,12,29,70,...)  |  Y: Linear (1,2,3,...)"


class SeriesMovement:
    """Movement logic where X follows the Pell sequence and Y increases linearly."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all sequence state to initial values."""
        # Pell: P(n) = 2*P(n-1) + P(n-2), starting P(0)=0, P(1)=1
        # Sequence: 0, 1, 2, 5, 12, 29, 70, 169, ...
        # We skip the leading 0 so first yielded value is 1.
        self._prev = 0             # P(n-2)
        self._curr = 1             # P(n-1)
        self._step = 0
        self.linear_step = 0
        self.last_x_step = 0
        self.last_y_step = 0

    def _next_pell(self):
        """
        Yield Pell numbers starting from 1: 1, 2, 5, 12, 29, 70, ...
        """
        self._step += 1

        if self._step == 1:
            # First call → yield 1
            self._prev = 0
            self._curr = 1
            return 1
        else:
            # P(n) = 2*P(n-1) + P(n-2)
            nxt = 2 * self._curr + self._prev
            self._prev = self._curr
            self._curr = nxt
            return nxt

    def get_next_step(self):
        """
        Advance sequences and return the next step sizes.
        Returns:
            (x_step, y_step): raw integer step values before direction/scale.
        """
        # Pell for X
        self.last_x_step = self._next_pell()

        # Linear for Y
        self.linear_step += 1
        self.last_y_step = self.linear_step

        return self.last_x_step, self.last_y_step

    def on_x_wall_hit(self):
        """Reset X (Pell) sequence when the searcher hits a left/right wall."""
        self._prev = 0
        self._curr = 1
        self._step = 0

    def on_y_wall_hit(self):
        """Reset Y (Linear) sequence when the searcher hits a top/bottom wall."""
        self.linear_step = 0

    def get_x_label(self):
        """Short label for X movement info in the HUD."""
        return "Pell X: {}".format(self.last_x_step)

    def get_y_label(self):
        """Short label for Y movement info in the HUD."""
        return "Lin Y: {}".format(self.last_y_step)

    def get_sequence_preview(self):
        """Return a string showing the sequence pattern for display."""
        prev, curr = 0, 1
        seq = [str(curr)]
        for _ in range(9):
            nxt = 2 * curr + prev
            prev, curr = curr, nxt
            seq.append(str(curr))
        return "X seq: " + ",".join(seq) + ",...  |  Y seq: 1,2,3,4,5,..."
