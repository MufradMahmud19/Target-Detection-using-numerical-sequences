# Target Detection Simulation

Target Detection is an interactive Python application built with OpenGL and GLUT. It visualizes a "searcher" trying to locate a specific target on a 2D plane. The unique aspect of this simulation is that the searcher's movement step sizes are governed by different mathematical series. 

By default, the X-axis movement follows complex sequences (like Fibonacci, Padovan, or Pell), while the Y-axis movement follows a simple linear sequence. Every time the searcher hits the screen's boundary, it bounces off and its sequence logic resets.

## Features

- **Mathematical Movement Sequences**: Observe how different mathematical series affect the traversal path of the searcher.
  - **Fibonacci Series**: X-axis steps follow the classic Fibonacci sequence (1, 1, 2, 3, 5, 8...), generating a golden-ratio based path.
  - **Padovan Series**: X-axis steps follow the Padovan sequence (1, 1, 1, 2, 2, 3, 4...), creating a spiral pattern related to the Plastic number.
  - **Pell Series**: X-axis steps follow the Pell numbers (1, 2, 5, 12, 29...), resulting in aggressive growth towards the Silver ratio.
- **Custom Rendering Pipeline**: Features custom-built graphical primitives, including Midpoint Line and Circle algorithms, glowing UI panels, and 7-segment style digit rendering.
- **Score Tracking**: Records your best times to reach specific targets across different series and saves them to a local Excel spreadsheet (`scores.xlsx`).
- **Extensible Architecture**: Easily add new movement logic by creating new `*_series.py` files. They are automatically discovered and loaded at runtime.

## Requirements

To run this simulation, you will need Python installed along with the following packages:
- `PyOpenGL`
- `PyOpenGL_accelerate` (optional but recommended for performance)
- `openpyxl` (for saving and tracking scores)

You can install the dependencies via pip:
```bash
pip install PyOpenGL openpyxl
```

## How to Run

1. Open your terminal or command prompt.
2. Navigate to the project directory.
3. Run the main script:
```bash
python main.py
```

## Usage Instructions

1. **Main Menu**: Upon launching, you will be greeted by the series selection menu. Press the corresponding number key to select which mathematical series the searcher will use for its movement.
2. **Set Target Position**: Type in the X and Y coordinates for your target within the allowed field range and press `ENTER`.
3. **Simulation**: Watch the searcher try to reach the target! The path taken, current elapsed time, and sequence steps are displayed on the HUD.
4. **Results Screen**: Once the target is caught, the results screen will display your time and let you know if you achieved a new high score for that particular target and sequence combination.
   - Press `R` to run again with the same target.
   - Press `N` to set a new target.
   - Press `M` to return to the main menu.
   - Press `X` to quit.

## Adding Custom Series

You can define your own mathematical series for the searcher to follow. 
1. Create a new Python file in the project directory ending with `_series.py` (e.g., `tribonacci_series.py`).
2. Define a `SERIES_NAME` variable and a `SeriesMovement` class inside the file.
3. The `SeriesMovement` class must implement `get_next_step()`, `on_x_wall_hit()`, `on_y_wall_hit()`, and a few other HUD helper methods. (Take a look at `fibonacci_series.py` as a working template).
4. Launch the application, and your new series will automatically appear in the main menu!

## Project Structure

- `main.py`: The entry point containing window management, rendering pipelines, state management, and the core simulation loop.
- `score_tracker.py`: Handles reading and writing high scores to `scores.xlsx` using `openpyxl`.
- `fibonacci_series.py`, `padovan_series.py`, `pell_series.py`: Modular files defining the mathematical movement logic for the searcher.
- Future extensions: The modular architecture allows additional numerical sequence modules to be implemented easily. More numerical sequences will be added in future versions without requiring changes to the core simulation engine.
