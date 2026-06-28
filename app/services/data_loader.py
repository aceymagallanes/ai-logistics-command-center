from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class DataLoader:
    """
    DataLoader is responsible for reading all logistics CSV files.

    This class centralizes data loading so the rest of the project does not need
    to know where the CSV files are stored.
    """

    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir

    def _load_csv(self, filename: str) -> pd.DataFrame:
        """
        Load a CSV file from the app/data folder.

        Args:
            filename: Name of the CSV file.

        Returns:
            pandas DataFrame containing the file data.

        Raises:
            FileNotFoundError if the file does not exist.
        """
        file_path = self.data_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Missing data file: {file_path}")

        return pd.read_csv(file_path)

    def load_orders(self) -> pd.DataFrame:
        return self._load_csv("orders.csv")

    def load_warehouses(self) -> pd.DataFrame:
        return self._load_csv("warehouses.csv")

    def load_inventory(self) -> pd.DataFrame:
        return self._load_csv("inventory.csv")

    def load_couriers(self) -> pd.DataFrame:
        return self._load_csv("couriers.csv")

    def load_delivery_history(self) -> pd.DataFrame:
        return self._load_csv("delivery_history.csv")

    def load_all(self) -> dict:
        """
        Load all core logistics datasets.

        Returns:
            Dictionary of dataset names and their DataFrames.
        """
        return {
            "orders": self.load_orders(),
            "warehouses": self.load_warehouses(),
            "inventory": self.load_inventory(),
            "couriers": self.load_couriers(),
            "delivery_history": self.load_delivery_history(),
        }
