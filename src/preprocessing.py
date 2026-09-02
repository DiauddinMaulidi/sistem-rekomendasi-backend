from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer

FEATURE_COLUMNS = [
    "pH_Tanah",
    "kelembaban",
    "ec",
    "nitrogen",
    "fosfor",
    "kalium",
    "suhuTanah",
    "jenisTanaman"
]

TARGET_COLUMN = "jenisPupuk"


def clean_dataset(df):

    columns_drop = [
        "Soil_Type",
        "Organic_Carbon",
        "Humidity",
        "Rainfall",
        "Crop_Growth_Stage",
        "Season",
        "Irrigation_Type",
        "Previous_Crop",
        "Region",
        "Fertilizer_Used_Last_Season",
        "Yield_Last_Season"
    ]

    return df.drop(columns_drop, axis=1)


def rename_columns(df):

    return df.rename(
        columns={
            "Soil_pH": "pH_Tanah",
            "Soil_Moisture": "kelembaban",
            "Electrical_Conductivity": "ec",
            "Nitrogen_Level": "nitrogen",
            "Phosphorus_Level": "fosfor",
            "Potassium_Level": "kalium",
            "Temperature": "suhuTanah",
            "Crop_Type": "jenisTanaman",
            "Recommended_Fertilizer": "jenisPupuk"
        }
    )


def translate_crop(df):

    df["jenisTanaman"] = df["jenisTanaman"].replace({
        "Cotton": "Kapas",
        "Maize": "Jagung",
        "Wheat": "Gandum",
        "Potato": "Kentang",
        "Rice": "Padi",
        "Sugarcane": "Tebu",
        "Tomato": "Tomat"
    })

    return df


def encode_target(df):

    encoder = LabelEncoder()

    y = encoder.fit_transform(df[TARGET_COLUMN])

    return y, encoder


def prepare_dataset(df):

    df = clean_dataset(df)

    df = rename_columns(df)

    df = translate_crop(df)

    X = df[FEATURE_COLUMNS]

    y, encoder = encode_target(df)

    return X, y, encoder


def preprocessing_pipeline():

    numeric_features = [
        "pH_Tanah",
        "kelembaban",
        "ec",
        "nitrogen",
        "fosfor",
        "kalium",
        "suhuTanah"
    ]

    categorical_features = [
        "jenisTanaman"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                StandardScaler(),
                numeric_features
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_features
            )
        ]
    )

    return preprocessor