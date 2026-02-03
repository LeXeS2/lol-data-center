# Research Notebooks

This directory contains Jupyter notebooks for research and analysis of League of Legends match data.

## Notebooks

### `win_probability_research.ipynb`

Comprehensive research notebook for win probability prediction using machine learning.

**Contents:**
1. Data exploration and role/champion analysis
2. PCA feature reduction with role context
3. Model training and comparison (Logistic Regression, Random Forest, SVM)
4. Performance evaluation and visualization
5. Outlier detection for surprising match outcomes
6. Model persistence for production deployment

**Requirements:**
```bash
pip install -e ".[research]"
```

**Usage:**
1. Ensure you have match data in the database
2. Start Jupyter Lab: `jupyter lab`
3. Open the notebook and run cells sequentially
4. Models will be saved to `../models/` directory

**Expected Outputs:**
- Trained prediction model
- Feature scaler and PCA transformer
- Performance metrics and visualizations
- Documentation of findings

## Running Notebooks

### Local Development

```bash
# Install dependencies
pip install -e ".[dev,research]"

# Start Jupyter Lab
jupyter lab

# Or use Jupyter Notebook
jupyter notebook
```

### With Docker

```bash
# Build and run with Jupyter
docker-compose run --service-ports lol-data-center jupyter lab --ip=0.0.0.0 --allow-root
```

## Data Requirements

The notebooks expect a PostgreSQL database with match data. See the main README for database setup instructions.

Minimum recommended data:
- At least 500 matches for basic analysis
- 1000+ matches for reliable model training
- Diverse champion and role representation

## Output Artifacts

Trained models are saved to `../models/` directory:
- `win_probability_model.pkl` - Trained classifier
- `scaler.pkl` - Feature scaler
- `pca.pkl` - PCA transformer (if used)

These can be loaded by the `WinProbabilityPredictor` service for production use.

## Tips

- Run all cells in order for reproducible results
- Adjust hyperparameters in model training cells as needed
- Use "Restart Kernel and Run All" for fresh runs
- Save results and visualizations as needed
- Check `docs/win_probability_research.md` for detailed findings
