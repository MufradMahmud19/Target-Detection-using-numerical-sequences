"""
Padovan Series Movement Module
================================
X-axis: Padovan sequence (1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12, 16, ...)
Y-axis: Linear sequence (1, 2, 3, 4, 5, ...)

The Rule:
  Each term is the sum of the two terms that are TWO and THREE
  steps back:  P(n) = P(n-2) + P(n-3)

  Starting values: P(0)=1, P(1)=1, P(2)=1

The Connection:
  The Padovan sequence generates the "Padovan spiral" of equilateral
  triangles, acting as a spiral-generating cousin to the Fibonacci
  spiral. It grows more slowly than Fibonacci (ratio converges to
  the Plastic number ~ 1.324 instead of the Golden Ratio ~ 1.618).

On wall hit: the corresponding sequence resets to the beginning.
"""

SERIES_NAME = "Padovan Series"
SERIES_KEY = "padovan"
SERIES_DESCRIPTION = "X: Padovan (1,1,1,2,2,3,4,5,7,...)  |  Y: Linear (1,2,3,...)"


class SeriesMovement:
    """Movement logic where X follows the Padovan sequence and Y increases linearly."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all sequence state to initial values."""
        # Padovan: P(n) = P(n-2) + P(n-3)
        # Sequence: 1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12, 16, ...
        # We keep three trailing values to compute the next one.
        self._p = [1, 1, 1]        # [P(n-3), P(n-2), P(n-1)]
        self._step = 0             # how many values yielded so far
        self.linear_step = 0
        self.last_x_step = 0
        self.last_y_step = 0

    def _next_padovan(self):
        """
        Yield Padovan numbers in order: 1, 1, 1, 2, 2, 3, 4, 5, 7, 9, ...

        First three are the seeds (1, 1, 1).
        From the fourth value onward: P(n) = P(n-2) + P(n-3).
        """
        self._step += 1

        if self._step <= 3:
            # Return the seed values
            return self._p[self._step - 1]
        else:
            # P(n) = P(n-2) + P(n-3)
            nxt = self._p[0] + self._p[1]
            # Shift window forward
            self._p[0] = self._p[1]
            self._p[1] = self._p[2]
            self._p[2] = nxt
            return nxt

    def get_next_step(self):
        """
        Advance sequences and return the next step sizes.
        Returns:
            (x_step, y_step): raw integer step values before direction/scale.
        """
        # Padovan for X
        self.last_x_step = self._next_padovan()

        # Linear for Y
        self.linear_step += 1
        self.last_y_step = self.linear_step

        return self.last_x_step, self.last_y_step

    def on_x_wall_hit(self):
        """Reset X (Padovan) sequence when the searcher hits a left/right wall."""
        self._p = [1, 1, 1]
        self._step = 0

    def on_y_wall_hit(self):
        """Reset Y (Linear) sequence when the searcher hits a top/bottom wall."""
        self.linear_step = 0

    def get_x_label(self):
        """Short label for X movement info in the HUD."""
        return "Pad X: {}".format(self.last_x_step)

    def get_y_label(self):
        """Short label for Y movement info in the HUD."""
        return "Lin Y: {}".format(self.last_y_step)

    def get_sequence_preview(self):
        """Return a string showing the sequence pattern for display."""
        # Generate Padovan numbers for preview
        p = [1, 1, 1]
        seq = list(p)
        for _ in range(9):
            nxt = p[0] + p[1]
            p[0], p[1], p[2] = p[1], p[2], nxt
            seq.append(nxt)
        return "X seq: " + ",".join(str(v) for v in seq) + ",...  |  Y seq: 1,2,3,4,5,..."
