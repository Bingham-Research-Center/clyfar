"""Class to download, hold, and manipulate GEFS forecast data."""

from herbie import Herbie

class GEFS:
    def __init__(self):
        pass

    def get_gefs_data(self,):
        # init_dt = datetime.datetime(2023, 12, 5, 18, 0, 0)

        H = Herbie(
            "2023-12-05 18:00",
            model="gefs",
            # product="atmos.5",
            product='atmos.25',
            # member="p01",
            # priority="google",
            # fxx=0,
            member="mean",
        )
        print(H)
        df = H.inventory()
        print(df)

if __name__ == "__main__":
    gefs = GEFS()
    gefs.get_gefs_data()
    pass