
import base64
from io import BytesIO

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from flask import Flask, render_template, request, flash, send_file

app = Flask(__name__)
app.secret_key = "retail_dashboard_secret_key"

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

REQUIRED_COLUMNS = [
    "Date", "Product", "Category",
    "Quantity", "UnitPrice", "Region"
]


def create_chart(data):

    category_sales = data.groupby("Category")["Sales"].sum()

    monthly_data = data.copy()
    monthly_data["Month"] = (
        monthly_data["Date"].dt.to_period("M").astype(str)
    )
    monthly_sales = monthly_data.groupby("Month")["Sales"].sum()

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    category_sales.plot(
        kind="bar",
        ax=axes[0],
        color="#3977D5"
    )

    axes[0].set_title("Sales by Category")
    axes[0].set_ylabel("Revenue")
    axes[0].set_xlabel("Category")
    axes[0].tick_params(axis="x", rotation=30)

    monthly_sales.plot(
        kind="line",
        marker="o",
        ax=axes[1],
        color="#16A085"
    )

    axes[1].set_title("Monthly Sales")
    axes[1].set_ylabel("Revenue")
    axes[1].set_xlabel("Month")
    axes[1].tick_params(axis="x", rotation=30)

    plt.tight_layout()

    image = BytesIO()
    fig.savefig(image, format="png", dpi=120)
    plt.close(fig)

    image.seek(0)

    return base64.b64encode(image.getvalue()).decode("utf-8")


def process_data(data):

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in data.columns
    ]

    if missing:
        raise ValueError(
            "Missing columns: " + ", ".join(missing)
        )

    data = data.copy()

    data["Date"] = pd.to_datetime(
        data["Date"], errors="coerce"
    )

    data["Quantity"] = pd.to_numeric(
        data["Quantity"], errors="coerce"
    )

    data["UnitPrice"] = pd.to_numeric(
        data["UnitPrice"], errors="coerce"
    )

    if data.empty:
        raise ValueError("CSV file is empty.")

    if data[["Date", "Quantity", "UnitPrice"]].isnull().any().any():
        raise ValueError("Please check dates and numbers in your CSV.")

    if (data["Quantity"] < 0).any() or (data["UnitPrice"] < 0).any():
        raise ValueError("Negative values are not allowed.")

    if (data["Quantity"] == 0).all():
        raise ValueError("Please provide at least one sale.")

    data["Sales"] = data["Quantity"] * data["UnitPrice"]

    total_sales = data["Sales"].sum()
    total_orders = len(data)
    total_quantity = data["Quantity"].sum()
    average_order = total_sales / total_orders

    chart = create_chart(data)

    table = data.head(20).copy()

    table["Date"] = table["Date"].dt.strftime("%Y-%m-%d")
    table["Sales"] = table["Sales"].map(
        lambda x: f"₹{x:,.2f}"
    )

    return {
        "total_sales": f"₹{total_sales:,.2f}",
        "total_orders": total_orders,
        "total_quantity": f"{total_quantity:,.0f}",
        "average_order": f"₹{average_order:,.2f}",
        "chart": chart,
        "table": table.to_dict(orient="records"),
        "columns": list(table.columns)
    }


@app.route("/", methods=["GET", "POST"])
def index():

    dashboard = None

    if request.method == "POST":

        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Please select a CSV file.")

        elif not file.filename.lower().endswith(".csv"):
            flash("Please upload only CSV files.")

        else:
            try:
                data = pd.read_csv(file)
                dashboard = process_data(data)

            except Exception as error:
                flash(f"Error: {error}")

    return render_template(
        "index.html",
        dashboard=dashboard
    )


@app.route("/download-sample")
def download_sample():

    return send_file(
        "sample_sales.csv",
        as_attachment=True,
        download_name="sample_sales.csv"
    )


if __name__ == "__main__":
    app.run(debug=True)
