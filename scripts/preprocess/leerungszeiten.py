from os.path import join, abspath, dirname, isdir
import pandas as pd
from matplotlib import pyplot as plt
from scipy.signal import savgol_filter
import datetime
from typing import Tuple


def get_sensor_data_dir() -> str:
    # Get the current script's directory
    script_dir = dirname(abspath(__file__))
    # script_dir = r"C:\Users\JumpStart\PycharmProjects\openhackSG_glasmuell\scripts\preprocess"

    data_dir = abspath(join(script_dir,
                                  '..', '..',
                                  'data', 'sensor'))
    assert isdir(data_dir)
    return data_dir


def detect_flanks_when_emptied(fill_percent: pd.Series):
    # Parameters for detection
    threshold_high = 35
    threshold_low = 20
    window_size = 48

    # Store timestamps of detected falling flanks
    falling_flank_timestamps = []

    # Check if the first and last entry in each window satisfy the criteria
    for i in range(window_size - 1, len(fill_percent)):
        window = fill_percent.iloc[i - window_size + 1: i + 1]
        window_start, window_end = window.index[0], window.index[-1]

        if (window.iloc[0] >= threshold_high) and (window.iloc[-1] < threshold_low):
            falling_flank_timestamps.append(window_start)

    # Use a boolean mask to filter entries where time diff is more than 24 hours
    timestamps = pd.Series(falling_flank_timestamps)
    time_diff = timestamps.diff()
    filtered_timestamps = timestamps[time_diff > pd.Timedelta(hours=24)]

    return filtered_timestamps


def process_color_dev(data_color_dev: pd.DataFrame,
                      device_id: str,
                      color: str) -> Tuple[list, tuple]:
    # Apply Savitzky-Golay filter to the non-NaN values
    window_length = 100  # Corresponds to 50 hours
    polyorder = 2  # Adjust as needed
    smoothed_data = savgol_filter(data_color_dev.data_distance, window_length, polyorder)
    data_color_dev["smoothed"] = smoothed_data

    # Convert smoothed data to relative percentages. 0% = Empty. 100% = Full
    min_mm: float = smoothed_data.max()  # Sensor reading in mm
    max_mm: float = smoothed_data.min()
    range_mm = abs(min_mm - max_mm)
    # Convert smoothed data to relative percentages
    fill_percent = abs(100 - ((smoothed_data - max_mm) / range_mm) * 100)
    data_color_dev["fill_percent"] = fill_percent
    flanks: list = detect_flanks_when_emptied(data_color_dev["fill_percent"])


    plt.figure(figsize=(7, 4))
    # # Plot vertical line for empty times
    # plt.vlines(flanks, ymin=0, ymax=3000,
    #            color="black", alpha=0.7,
    #            label="Entleerung")
    plt.plot(data_color_dev.index,
             data_color_dev.data_distance,
             label="Rohdaten", alpha=0.4)

    plt.plot(data_color_dev.index,
             smoothed_data,
             label="Gefiltert")
    for flank in flanks:
        entleer_marker = data_color_dev[data_color_dev.index.isin([flank])]['smoothed']
        if len(entleer_marker) == 1 and len([flank]) == 1:
            plt.scatter([flank], [entleer_marker],
                        color="black", marker="s")

    plt.title(f"{color}glas Sensor {device_id[:6]}")
    plt.ylabel("Distanzmessung in mm")

    plt.legend(loc='upper right')
    # Set x-axis limits using plt.xlim()
    start_date = datetime.datetime(2023, 1, 1)
    end_date = datetime.datetime(2023, 12, 1)
    quarters = pd.date_range(start=start_date, end=end_date, freq='QS')
    plt.xticks(quarters)
    plt.xlim(start_date, end_date)
    plt.ylim([smoothed_data.max(), smoothed_data.min()])

    plt.savefig(f"{color}glas {device_id}")

    return flanks.tolist(), [min_mm, max_mm]


def iterate_preprocess():
    # Data Braunglas as json
    brown_json = join(get_sensor_data_dir(),
                      "fuellstandsensoren-glassammelstellen-braunglas.json")

    # Data Weissglas
    white_json = join(get_sensor_data_dir(),
                      "fuellstandsensoren-glassammelstellen-weissglas.json")

    # Data Grünglas
    green_json = join(get_sensor_data_dir(),
                      "fuellstandsensoren-glassammelstellen-gruenglas.json")

    for color, json_file in zip(
            ["Braun", "Weiss", "Grün"],
            [brown_json, white_json, green_json]):
        df = pd.read_json(json_file)
        result_timestamps: dict = dict()
        min_max_distance: dict = dict()
        color: str
        df: pd.DataFrame
        # Drop rows where 'data_distance' is NaN
        df = df.dropna(subset=['data_distance'])
        df = df[df['data_distance'] != 2500]
        # Convert the "measured_at" column to datetime format
        df['measured_at'] = pd.to_datetime(df['measured_at'], utc=True)
        # Set the "measured_at" column as the datetime index
        df.set_index('measured_at', inplace=True)
        for device_id in df.device_id.unique():
            device_id: str
            # Filter rows in df where device_id matches the current iteration
            data_color_dev = df[df['device_id'] == device_id].copy()
            data_color_dev.sort_index(inplace=True)

            # Resetting the index to convert datetime index to a column
            data_color_dev.reset_index(inplace=True)
            data_color_dev.to_json(join(get_sensor_data_dir(), "sample brown.json"),
                                   orient='records', date_format='iso')
            data_color_dev.set_index('measured_at', inplace=True)

            timestamps, min_max_mm = process_color_dev(data_color_dev, device_id, color)
            plt.clf()
            timestamps: list
            min_max_mm: list
            min_max_distance[device_id] = min_max_mm

            result_timestamps[device_id] = pd.Series(timestamps)

        min_max_distance: pd.DataFrame = pd.DataFrame(min_max_distance)
        min_max_distance.index = ['empty', 'full']
        min_max_distance.to_csv(f"Min Max {color}.csv")

        result_timestamps: pd.DataFrame = pd.DataFrame(result_timestamps)
        result_timestamps.to_csv(f"Leerungszeitpunkte {color}glas.csv", index=False)


if __name__ == "__main__":
    iterate_preprocess()

    df_color_dev = pd.read_json(join(get_sensor_data_dir(), "sample brown.json"),
                                orient='records')
    df_color_dev.set_index('measured_at', inplace=True)

    print(process_color_dev(df_color_dev, "Test", "Braun"))
    plt.show()

