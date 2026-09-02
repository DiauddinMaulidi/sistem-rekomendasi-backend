import os
import joblib
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from datetime import date, datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from api.api import (
    data_dummy,
    get_latest_sensor,
    insert_recommendation,
    hitung_dosis,
    get_latest_rek,
    statistic_pupuk,
    get_latest_recommendation,
    post_lahan,
    get_lahan,
    upload_gambar,
    id_get_lahan,
    update_lahan,
    delete_lahan,
    get_grafik_sensor,
    insert_dataset
)

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "models" / "fertilizer_pipeline.pkl"
LABEL_ENCODER = BASE_DIR / "models" / "label_encoder.pkl"

pipeline = joblib.load(MODEL_PATH)
encoder = joblib.load(LABEL_ENCODER)

app = FastAPI()

load_dotenv()
FRONTEND_URLS = os.getenv("FRONTEND_URLS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hari_ini = date.today()
last_sensor_save = None

class SensorData(BaseModel):
    sensor_id: str

    pH_Tanah: float
    kelembaban: float
    ec: float
    nitrogen: float
    fosfor: float
    kalium: float
    suhuTanah: float

class RecommendationRequest(BaseModel):
    sensor_id: str
    jenisPupuk: str
    dosis: float
    tanggal: date


class LahanRequest(BaseModel):
    nama: str
    luas: float
    tanaman: str
    sensor: str
    lokasi: str

@app.get("/")
def home():
    return {
        "message": "API Running"
    }

@app.post("/sensor/dummy")
def dummy_sensor():
    try:
        data = data_dummy()

        result = insert_dataset(data)

        return {
            "success": True,
            "message": "Data dummy berhasil disimpan",
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        print("ERROR DUMMY SENSOR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/sensor/data")
def receive_sensor_data(data: SensorData):

    try:
        # Ubah Pydantic model menjadi dictionary
        sensor_data = data.model_dump()

        # Simpan ke dataset
        result = insert_dataset(sensor_data)

        return {
            "success": True,
            "message": "Data sensor berhasil disimpan",
            "data": result
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        print("ERROR SENSOR:", e)

        raise HTTPException(
            status_code=500,
            detail="Gagal menyimpan data sensor"
        )

@app.get("/sensor")
async def get_rek():
    return get_latest_rek()

@app.get("/sensor/latest/{sensor_id}")
def latest_sensor(sensor_id: str):
    sensor = get_latest_sensor(sensor_id)

    if sensor is None:
        return {
            "message": "Belum ada data sensor."
        }

    return sensor

@app.post("/predict/{sensor_id}")
def predict(sensor_id: str):
    sensor = get_latest_sensor(sensor_id)

    if sensor is None:
        return {
            "message": "Belum ada data sensor."
        }

    df = pd.DataFrame([{
        "pH_Tanah": sensor["pH_Tanah"],
        "kelembaban": sensor["kelembaban"],
        "ec": sensor["ec"],
        "nitrogen": sensor["nitrogen"],
        "fosfor": sensor["fosfor"],
        "kalium": sensor["kalium"],
        "suhuTanah": sensor["suhuTanah"],
        "jenisTanaman": sensor["jenisTanaman"],
        "tanggal": hari_ini.isoformat(),
    }])

    prediction = pipeline.predict(df)

    fertilizer = encoder.inverse_transform(
        prediction
    )[0]

    dosis = hitung_dosis(
        sensor,
        fertilizer
    )

    return {
        "sensor_id": sensor["sensor_id"],
        "jenisPupuk": fertilizer,
        "dosis": dosis,
        "tanggal": hari_ini.isoformat(),
    }

@app.post("/recommendation/save")
def save_recommendation(
    data: RecommendationRequest
):
    result = insert_recommendation(
        data.model_dump(mode="json")
    )

    return {
        "message": "Success",
        "data": result,
    }

@app.get("/statistic")
def statistic_jumlah():
    return statistic_pupuk()
    
@app.get("/recommendation/last")
def last_rekomendation():
    return get_latest_recommendation()


@app.post("/lahan/tambah/save")
async def tambah_lahan(
    nama: str = Form(...),
    luas: float = Form(...),
    lokasi: str = Form(...),
    tanaman: str = Form(...),
    sensor: str = Form(...),
    gambar: UploadFile = File(...)
):
    isi_file = await gambar.read()

    image_url = upload_gambar(
        file_bytes=isi_file,
        filename=gambar.filename,
        content_type=gambar.content_type
    )

    payload = {
        "nama": nama,
        "luas": luas,
        "lokasi": lokasi,
        "tanaman": tanaman,
        "sensor": sensor,
        "gambar": image_url,
        "tanggal": date.today().isoformat()
    }

    result = post_lahan(payload)

    return {
        "message": "Success",
        "data": result.data
    }

@app.get("/lahan/tambah/get")
def lihat_result():
    return get_lahan()

@app.get("/lahan/edit/{id}")
def get_all_lahan(id: int):
    return id_get_lahan(id)

@app.put("/lahan/edit/{id}")
async def update_lahan_endpoint(
    id: int,
    nama: str = Form(...),
    luas: float = Form(...),
    lokasi: str = Form(...),
    tanaman: str = Form(...),
    sensor: str = Form(...),
    tanggal: str = Form(...),
    gambar: Optional[UploadFile] = File(None),
):
    try:
        data = {
            "nama": nama,
            "luas": luas,
            "lokasi": lokasi,
            "tanaman": tanaman,
            "sensor": sensor,
            "tanggal": tanggal,
        }

        # Kalau user memilih gambar baru
        if gambar is not None:
            file_bytes = await gambar.read()

            public_url = upload_gambar(
                file_bytes=file_bytes,
                filename=gambar.filename,
                content_type=gambar.content_type,
            )

            data["gambar"] = public_url

        result = update_lahan(id, data)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Data lahan tidak ditemukan",
            )

        return {
            "message": "Data lahan berhasil diperbarui",
            "data": result,
        }

    except HTTPException:
        raise

    except Exception as e:
        print("Error update lahan:", e)

        raise HTTPException(
            status_code=500,
            detail="Gagal memperbarui data lahan",
        )

@app.get("/sensor/grafik/{sensor_id}")
def grafik_sensor(sensor_id: str):
    data = get_grafik_sensor(sensor_id)

    return data

@app.delete("/lahan/{id}")
def delete_lahan_endpoint(id: int):

    try:
        result = delete_lahan(id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Data lahan tidak ditemukan"
            )

        return {
            "message": "Data lahan berhasil dihapus",
            "data": result
        }

    except HTTPException:
        raise

    except Exception as e:
        print("Error hapus lahan:", e)

        raise HTTPException(
            status_code=500,
            detail="Gagal menghapus data lahan"
        )