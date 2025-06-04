# Bank Statement Categorisor
Trains and applies Machine Learning models to categorise bank statements.

## Setting up
1. Clone the repository: 

   `git clone https://github.com/twhi/bank-statement-categoriser.git`
   
2. `cd` into the repo
3. Install a virtual environment:

   `virtualenv venv`

4. Activate virtual environment:
   
   `venv\scripts\activate` (Windows) 

5. Install requirements:

   `pip install -r requirements.txt`
   
## Usage
Once you have completed the above steps, call `main.py` to start the program (your virtual environment will need to be active). This tool has 2 main modes of operation:
### Train model
To train a new Machine Learning model, you will need to provide training data to the program. The training data itself needs to be CSV format and must contain the 2 following columns (it can contain more, but these will be ignored):
1. 'Description' - this column will contain the transaction description as per your bank statement
2. 'Category' - this column will contain the category which each transaction belongs to.

An example of some training data is shown below:

```
Description		        Category
MCDONALDS, OXFORD GB		FOOD
TESCO STORES, BICESTER GB	FOOD
THE COWLEY RETREAT		PUB
SAINSBURYS PETROL	        CAR
TBS BANK 04JUN			ATM
STAGECOACH, BUS TICKET		TRAVEL
```

You'll want to use at least 100 manually categorised transactions for the model to produce useful predictions. The more you can provide, the better the predictions. Any training data that you subsequently supply will be appended to any existing training data that you might have added before - this will allow your predictions to get better the more you use the tool. If you wish to start a new model, you will need to manually delete any existing data by deleting the database file located at `./data/app.db`.

### Categorise bank statement
To categorise a bank statement, you will need to have already trained a categorisation model (see above). The bank statement itself must contain a column called ‘Description’ which contains the transaction descriptions. If you meet both of these criteria, the program will take your input bank statement, categorise each transaction, and also provide a confidence score for each prediction. The results will be output out to `./data/test_results.csv`.
