from fastapi import FastAPI, UploadFile, HTTPException, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from joblib import load
import pandas as pd
from io import StringIO
import re
import warnings
warnings.filterwarnings("ignore")

clf = load('trained_pipeline.joblib')

class CarDataPreprocessor:
    def __init__(self):
        pass

    def preprocess_columns(self, df, columns):
        for column in columns:
            df[column] = df[column].apply(
                lambda x: float(re.search(r'\d+(\.\d+)?', x).group(0)) if isinstance(x, str) and re.search(r'\d+(\.\d+)?', x) else None
            )

    def extract_max_torque_rpm(self, torque_str):
        if isinstance(torque_str, str):
            rpm_pattern = r'@?\s*([\d,]+)\s*\(?(?:kgm@)?\s*rpm\)?'
            rpm_match = re.search(rpm_pattern, torque_str)
            if rpm_match:
                return int(rpm_match.group(1).replace(",", ""))
        return None

    def extract_and_convert_torque_value(self, torque_str):
        if isinstance(torque_str, str):
            value_pattern = r'(\d+\.\d+|\d+)\s*(kgm|nm|Nm)?\s*(?:@|at|\()'
            value_match = re.search(value_pattern, torque_str, re.IGNORECASE)
            if value_match:
                value = float(value_match.group(1))
                unit = value_match.group(2)
                if unit and unit.lower() == 'kgm' or 'kgm' in torque_str.lower():
                    value *= 9.81
                return value
        return None

    def preprocess_torque(self, df):
        df['max_torque_rpm'] = df['torque'].apply(self.extract_max_torque_rpm)
        df['torque'] = df['torque'].apply(self.extract_and_convert_torque_value)

    def preprocess_name(self, df):
        df['name'] = df['name'].apply(lambda x: x.split()[0])

    def preprocess_all(self, df, columns_to_preprocess=['mileage', 'engine', 'max_power']):
        self.preprocess_columns(df, columns_to_preprocess)
        self.preprocess_torque(df)
        self.preprocess_name(df)
        return df

class Item(BaseModel):
    name: str
    year: int
    km_driven: int
    fuel: str
    seller_type: str
    transmission: str
    owner: str
    mileage: str
    engine: str
    max_power: str
    torque: str
    seats: float

class Items(BaseModel):
    objects: List[Item]

app = FastAPI()
preprocessor = CarDataPreprocessor()

@app.get("/")
def get_status():
    """
    Проверка статуса API.
    """
    return {"status": "OK", "message": "Car price prediction API is running"}

@app.post("/predict_item")
def predict_item(item: Item) -> float:
    """
    Прогноз стоимости по одному объекту.
    """
    try:
        item_df = pd.DataFrame([item.dict()])
        item_df = preprocessor.preprocess_all(item_df)
        prediction = clf.predict(item_df)[0]
        return prediction
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/predict_items_csv")
def predict_items_csv(file: UploadFile = File(...)) -> StreamingResponse:
    """
    Загрузка CSV-файла с признаками объектов, возврат файла с предсказаниями.
    """
    try:

        contents = file.file.read().decode('utf-8')
        df = pd.read_csv(StringIO(contents))

        df = preprocessor.preprocess_all(df)

        df['predicted_price'] = clf.predict(df)

        output_stream = StringIO()
        df.to_csv(output_stream, index=False)
        output_stream.seek(0)

        return StreamingResponse(
            iter([output_stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=predictions.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        file.file.close()