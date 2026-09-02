import os
from supabase import create_client, Client
from collections import Counter
from datetime import date, datetime
import uuid
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL dan SUPABASE_KEY wajib diisi di file .env")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

TARGET_N = 80
TARGET_P = 60
TARGET_K = 60


def data_dummy():
    return {
        "sensor_id": "ESP32-003",
        "pH_Tanah": 6.2,
        "kelembaban": 45.5,
        "ec": 1.8,
        "nitrogen": 90,
        "fosfor": 40,
        "kalium": 20,
        "suhuTanah": 27.5,
    }

def insert_sensor(sensor):
    result = (
        supabase
        .table("dataset")
        .insert({
            "sensor_id": sensor.sensor_id,
            "pH_Tanah": sensor.pH_Tanah,
            "kelembaban": sensor.kelembaban,
            "ec": sensor.ec,
            "nitrogen": sensor.nitrogen,
            "fosfor": sensor.fosfor,
            "kalium": sensor.kalium,
            "suhuTanah": sensor.suhuTanah,
            "jenisTanaman": sensor.jenisTanaman,
        })
        .execute()
    )

    return result.data


def get_latest_sensor(sensor_id: str):
    result = (
        supabase
        .table("dataset")
        .select("*")
        .eq("sensor_id", sensor_id)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]

    return None

def get_all_sensor(sensor_id: str):
    result = (
        supabase
        .table("dataset")
        .select("*")
        .eq("sensor_id", sensor_id)
        .order("id", desc=False)
        .limit(30)
        .execute()
    )

    return result.data

def get_latest_rek():
    result = (
        supabase
        .table("recommendation")
        .select("*", count="exact")
        .order("id", desc=True)
        .execute()
    )
    return {
        "data": result.data,
        "count": result.count
    }

def statistic_pupuk():
    result = (
        supabase
        .table("recommendation")
        .select("jenisPupuk")
        .execute()
    )

    data = result.data
    counter = Counter(item["jenisPupuk"] for item in data)

    if counter:
        pupuk, jumlah = counter.most_common(1)[0]
    else:
        pupuk, jumlah = None, 0
    
    return {
        "jenisPupuk": pupuk,
        "jumlah": jumlah
    }

def insert_recommendation(data):
    sensor_code = data["sensor_id"]

    dataset_id = get_latest_dataset_id(sensor_code)

    recommendation_data = {
        "sensor_id": dataset_id,
        "jenisPupuk": data["jenisPupuk"],
        "dosis": data["dosis"],
        "tanggal": data["tanggal"],
    }

    return (
        supabase
        .table("recommendation")
        .insert(recommendation_data)
        .execute()
    )

def hitung_dosis(sensor, fertilizer):
    if fertilizer == "Urea":
        defisit = max(0, TARGET_N - sensor["nitrogen"])
        dosis = defisit / 0.46
    elif fertilizer == "DAP":
        defisit = max(0, TARGET_P - sensor["fosfor"])
        dosis = defisit / 0.46
    elif fertilizer == "MOP":
        defisit = max(0, TARGET_K - sensor["kalium"])
        dosis = defisit / 0.60
    elif fertilizer == "NPK":
        n = max(0, TARGET_N - sensor["nitrogen"])
        p = max(0, TARGET_P - sensor["fosfor"])
        k = max(0, TARGET_K - sensor["kalium"])
        dosis = max(
            n / 0.15,
            p / 0.15,
            k / 0.15
        )
    elif fertilizer == "Compost":
        dosis = 3000
    elif fertilizer == "Zinc Sulphate":
        dosis = 25
    else:
        dosis = 0
    return round(dosis, 2)

def get_latest_recommendation():
    result = (
        supabase
        .table("recommendation")
        .select("*")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]
    return None

def get_lahan_by_sensor(sensor_id: str):
    response = (
        supabase
        .table("lahan")
        .select("*")
        .eq("sensor", sensor_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]

def insert_dataset(data: dict):
    sensor_id = data.get("sensor_id")

    if not sensor_id:
        raise ValueError("sensor_id wajib diisi")

    lahan = get_lahan_by_sensor(sensor_id)

    if not lahan:
        raise ValueError(
            f"Lahan dengan sensor '{sensor_id}' tidak ditemukan"
        )

    jenis_tanaman = lahan.get("tanaman")

    if not jenis_tanaman:
        raise ValueError(
            f"Jenis tanaman untuk sensor '{sensor_id}' belum tersedia"
        )

    # --------------------------------------------------------
    # Bentuk data untuk tabel dataset
    # --------------------------------------------------------

    dataset_data = {
        "pH_Tanah": data.get("pH_Tanah"),
        "kelembaban": data.get("kelembaban"),
        "ec": data.get("ec"),
        "nitrogen": data.get("nitrogen"),
        "fosfor": data.get("fosfor"),
        "kalium": data.get("kalium"),
        "suhuTanah": data.get("suhuTanah"),

        # Diambil dari tabel LAHAN
        "jenisTanaman": jenis_tanaman,

        # Kode ESP32
        "sensor_id": sensor_id,

        # Kalau sudah diberikan dari endpoint, gunakan.
        # Kalau tidak, gunakan waktu sekarang.
        "tanggal": datetime.now().date().isoformat(),
    }

    response = (
        supabase
        .table("dataset")
        .insert(dataset_data)
        .execute()
    )

    if not response.data:
        raise ValueError("Gagal menyimpan data sensor ke dataset")

    return response.data[0]

def get_latest_dataset_by_sensor(sensor_id: str):
    response = (
        supabase
        .table("dataset")
        .select("*")
        .eq("sensor_id", sensor_id)
        .order("tanggal", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]

def get_latest_dataset_id(sensor_id: str):
    """
    Mengambil ID dataset terbaru.

    Nilai ini yang akan disimpan ke:
    recommendation.sensor_id
    """

    dataset = get_latest_dataset_by_sensor(sensor_id)

    if not dataset:
        raise ValueError(
            f"Dataset untuk sensor '{sensor_id}' tidak ditemukan"
        )

    dataset_id = dataset.get("id")

    if dataset_id is None:
        raise ValueError(
            f"ID dataset untuk sensor '{sensor_id}' tidak ditemukan"
        )

    return dataset_id


# ============================================================
# 5. MENYIMPAN REKOMENDASI PEMUPUKAN
# ============================================================

def insert_recommendation(data: dict):
    """
    Menyimpan rekomendasi pemupukan.

    Frontend mengirim:
        sensor_id = "ESP32-002"

    Tetapi tabel recommendation membutuhkan:
        sensor_id = int8

    Maka:
        ESP32-002
            ↓
        dataset terbaru
            ↓
        dataset.id
            ↓
        recommendation.sensor_id
    """

    sensor_code = data.get("sensor_id")

    if not sensor_code:
        raise ValueError("sensor_id wajib diisi")

    # --------------------------------------------------------
    # Cari dataset terbaru
    # --------------------------------------------------------

    dataset_id = get_latest_dataset_id(sensor_code)

    # --------------------------------------------------------
    # Pastikan tanggal aman untuk JSON
    # --------------------------------------------------------

    tanggal = data.get("tanggal")

    if isinstance(tanggal, (date, datetime)):
        tanggal = tanggal.isoformat()

    # --------------------------------------------------------
    # Data yang benar untuk tabel recommendation
    # --------------------------------------------------------

    recommendation_data = {
        "sensor_id": dataset_id,
        "jenisPupuk": data.get("jenisPupuk"),
        "dosis": data.get("dosis"),
        "tanggal": tanggal,
    }

    # --------------------------------------------------------
    # Insert
    # --------------------------------------------------------

    response = (
        supabase
        .table("recommendation")
        .insert(recommendation_data)
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Gagal menyimpan rekomendasi"
        )

    return response.data[0]

def post_lahan(data):
    result = (
        supabase
        .table("lahan")
        .insert(data)
        .execute()
    )

    return result


def update_lahan(id: int, data: dict):
    result = (
        supabase
        .table("lahan")
        .update(data)
        .eq("id", id)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]


def get_lahan():
    result = (
        supabase
        .table("lahan")
        .select("*")
        .order("id", desc=True)
        .execute()
    )

    return result


def id_get_lahan(id: int):
    result = (
        supabase
        .table("lahan")
        .select("*")
        .eq("id", id)
        .single()
        .execute()
    )

    return result.data

def delete_lahan(id: int):
    result = (
        supabase
        .table("lahan")
        .delete()
        .eq("id", id)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]

def upload_gambar(file_bytes, filename, content_type):

    ext = filename.split(".")[-1]
    nama_file = f"{uuid.uuid4()}.{ext}"

    supabase.storage.from_("Image").upload(
        path=nama_file,
        file=file_bytes,
        file_options={
            "content-type": content_type
        }
    )

    public_url = (
        supabase.storage
        .from_("Image")
        .get_public_url(nama_file)
    )

    return public_url

def get_grafik_sensor(sensor_id: str):
    result = supabase.table("dataset") \
        .select("*") \
        .eq("sensor_id", sensor_id) \
        .order("tanggal", desc=False) \
        .execute()

    return result.data
