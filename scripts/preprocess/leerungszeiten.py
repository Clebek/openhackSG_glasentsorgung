from os.path import join, abspath, dirname, isdir
import pandas as pd
from matplotlib import pyplot as plt
from scipy.signal import savgol_filter


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
    threshold_low = 15
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
                      color: str) -> list:
    # Apply Savitzky-Golay filter to the non-NaN values
    window_length = 100  # Adjust as needed
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

    plt.subplot(2, 1, 1)
    plt.plot(data_color_dev.index,
             data_color_dev.data_distance,
             label="Rohdaten", alpha=0.5)
    # ax = data_color_dev['data_distance'].plot(label='Original Data')

    plt.plot(data_color_dev.index,
             smoothed_data,
             label="Gefiltert")
    # data_color_dev.smoothed.plot(ax=ax, label='Smoothed Data')

    plt.title(f"{color}glas")
    plt.ylabel("Distanz Glas vom Sensor in mm")
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.plot(data_color_dev.index,
             fill_percent)
    plt.vlines(flanks, ymin=0, ymax=100, color="r")
    plt.savefig(f"{color}glas {device_id}")
    plt.clf()
    return flanks.tolist()


def iterate_preprocess():
    brown_json = join(get_sensor_data_dir(),
                      "fuellstandsensoren-glassammelstellen-braunglas.json")
    df_brown = pd.read_json(brown_json)
    result_timestamps: dict = dict()

    for color, df in zip(["Braun"], [df_brown]):
        color: str
        df: pd.DataFrame
        # Drop rows where 'data_distance' is NaN
        df = df.dropna(subset=['data_distance'])
        df = df[df['data_distance'] != 2500]
        # Convert the "measured_at" column to datetime format
        df['measured_at'] = pd.to_datetime(df['measured_at'])
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

            timestamps: list = process_color_dev(data_color_dev, device_id, color)
            result_timestamps[device_id] = pd.Series(timestamps)

        result_timestamps: pd.DataFrame = pd.DataFrame(result_timestamps)
        result_timestamps.to_csv(f"Leerungszeitpunkte {color}glas.csv", index=False)


if __name__ == "__main__":
    iterate_preprocess()

    # df_color_dev = pd.read_json(join(get_sensor_data_dir(), "sample brown.json"),
    #                             orient='records')
    # df_color_dev.set_index('measured_at', inplace=True)
    #
    # process_color_dev(df_color_dev, None, "Braun")
    # plt.show()

