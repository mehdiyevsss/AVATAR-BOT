# AVATAR-BOT

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mehdiyevsss/AVATAR-BOT.git
cd AVATAR-BOT
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

- `app.py`: Main Flask application
- `index_builder.py`: Script for building the FAISS index
- `src/`: Source code directory
- `static/`: Static files (CSS, JS, etc.)
- `embeddings/`: Directory for storing embeddings
- `data/`: Data directory

## Running the Application

1. Make sure you have activated your virtual environment
2. Run the Flask application:
```bash
python app.py
```

