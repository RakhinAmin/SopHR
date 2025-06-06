from tkinter import Tk
from tkinter.filedialog import askopenfilename
import pandas as pd
import pickle
from sqlalchemy.orm import sessionmaker
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import chardet

from models import *
from exceptions import *

# ─────────── Encoding Helper ───────────

def read_csv_with_fallback(filepath):
    with open(filepath, 'rb') as f:
        encoding = chardet.detect(f.read())['encoding'] or 'utf-8'
    try:
        return pd.read_csv(filepath, encoding=encoding)
    except Exception:
        return pd.read_csv(filepath, encoding='ISO-8859-1')


class Train:
    def __init__(self, fp):
        self.filepath = fp
        self.categories = None

        try:
            new_data = self._get_new_data()
        except InvalidTrainingData as e:
            raise e

        DBSession = sessionmaker(bind=engine)
        self.session = DBSession()

        existing_data = self._get_database_as_df()

        all_data = pd.concat([existing_data, new_data], axis=0, sort=True)
        all_data.drop_duplicates(subset=['description', 'category'], inplace=True)

        self._write_df_to_database(all_data)

        trained_model = self.evaluate_model(all_data)
        self._save_trained_model(trained_model)

        print('Model successfully trained.')

    def _save_trained_model(self, mdl):
        with open('data/trained_svm.pkl', 'wb') as f:
            pickle.dump(mdl, f)

    def train_model(self, df):
        text_clf = Pipeline([
            ('vect', CountVectorizer(ngram_range=(1, 2), stop_words='english', max_features=5000)),
            ('tfidf', TfidfTransformer()),
            ('clf-svm', SGDClassifier(
                loss='log_loss',
                penalty='l2',
                alpha=1e-4,
                max_iter=1000,
                class_weight='balanced',
                random_state=42
            ))
        ])
        return text_clf

    def evaluate_model(self, df):
    # Drop rows with missing descriptions or categories
        df = df.dropna(subset=['description', 'category'])
        df['description'] = df['description'].astype(str)

        X_train, X_test, y_train, y_test = train_test_split(
            df['description'], df['category'], test_size=0.2, random_state=42
        )

        model = self.train_model(df)

    # Drop NaNs and convert to string (defensive check)
        X_train = X_train.dropna().astype(str)
        y_train = y_train[X_train.index]
        X_test = X_test.dropna().astype(str)
        y_test = y_test[X_test.index]

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        print(classification_report(y_test, y_pred))
        return model


    def _write_df_to_database(self, df):
        df.to_sql('TrainingData', self.session.bind, if_exists='replace', index=False)

    def _get_database_as_df(self):
        return pd.read_sql(self.session.query(Training).statement, self.session.bind)

    def _get_new_data(self):
        if self.filepath == '':
            raise InvalidTrainingData('No file specified')

        df = read_csv_with_fallback(self.filepath)
        df.columns = map(str.lower, df.columns)
        df.columns = map(str.strip, df.columns)

        if 'description' in df.columns and 'category' in df.columns:
            return df
        else:
            raise InvalidTrainingData("CSV must contain 'Description' and 'Category' headers.")


class Categorise:
    CONFIDENCE_THRESHOLD = 0.3  # You can tune this

    def __init__(self, fp):
        self.filepath = fp

        try:
            test_data = self._get_test_data()
        except InvalidBankStatement as e:
            raise e

        try:
            self.model = self._get_svm_model()
        except FileNotFoundError as e:
            raise e

        # Make predictions
        predicted_probs = self.model.predict_proba(test_data['description'])
        predicted_labels = self.model.predict(test_data['description'])
        max_probs = predicted_probs.max(axis=1)

        # Apply thresholding
        predicted_final = [
            label if prob >= self.CONFIDENCE_THRESHOLD else "Uncategorised"
            for label, prob in zip(predicted_labels, max_probs)
        ]

        test_data['predicted_category'] = predicted_final
        test_data['probability'] = max_probs

        self._save_results(test_data)

    def _save_results(self, d):
        while True:
            try:
                d.to_csv('data/test_results.csv', encoding='utf-8-sig', index=False)
                break
            except PermissionError as e:
                input(f"❌ Close the file: {e.filename}, then press Enter to retry...")

    def _get_test_data(self):
        if self.filepath == '':
            raise InvalidBankStatement('No file specified')

        df = read_csv_with_fallback(self.filepath)
        df.columns = map(str.lower, df.columns)
        df.columns = map(str.strip, df.columns)

        if 'description' not in df.columns:
            raise InvalidBankStatement("CSV must contain a 'Description' column.")

        df = df.dropna(subset=['description'])
        df['description'] = df['description'].astype(str)
        return df

    def _get_svm_model(self):
        with open('./data/trained_svm.pkl', "rb") as input_file:
            m = pickle.load(input_file)
        if isinstance(m, Pipeline):
            return m
        else:
            raise InvalidModelError('The detected model is not compatible.')


if __name__ == '__main__':
    while True:
        session_type = input('Select an option:\n'
                             '[1] - Categorise a bank statement (requires a trained model)\n'
                             '[2] - Train the categorisation model\n\n'
                             'Choice: ')

        if session_type == '1':
            fp = get_data_path()
            Categorise(fp)
            break
        elif session_type == '2':
            fp = get_data_path()
            Train(fp)
            break
        else:
            print('Invalid selection, please try again...\n')
