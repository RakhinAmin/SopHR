from tkinter import Tk
from tkinter.filedialog import askopenfilename
import pandas as pd
import pickle
from sqlalchemy.orm import sessionmaker

from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline

from models import *
from exceptions import *


class Train:

    def __init__(self, fp):
        self.filepath = fp
        self.categories = None

        # get data from specified filepath as dataframe
        try:
            new_data = self._get_new_data()
        except InvalidTrainingData as e:
            raise e

        # if data is valid then start DB session
        DBSession = sessionmaker(bind=engine)
        self.session = DBSession()

        # get existing data from DB as dataframe
        existing_data = self._get_database_as_df()

        # combine new data with old data
        all_data = pd.concat([existing_data, new_data], axis=0, sort=True)

        # drop the duplicates from the combined data set
        all_data.drop_duplicates(subset=['description', 'category'], inplace=True)

        # write to database
        self._write_df_to_database(all_data)

        # train model with training data
        trained_model = self.train_model(all_data)

        # save trained model
        self._save_trained_model(trained_model)

        print('Model successfully trained.')

    def _save_trained_model(self, mdl):
        with open('data/trained_svm.pkl', 'wb') as f:
            pickle.dump(mdl, f)

    def train_model(self, df):
        text_clf_svm = Pipeline([
            ('vect', CountVectorizer()),
            ('tfidf', TfidfTransformer()),
            ('clf-svm', SGDClassifier(loss='modified_huber', penalty='l2', alpha=1e-3, max_iter=10, random_state=42))
        ])
        return text_clf_svm.fit(df.description, df.category)

    def _write_df_to_database(self, df):
        df.to_sql('TrainingData', self.session.bind, if_exists='replace', index=False)

    def _get_database_as_df(self):
        return pd.read_sql(self.session.query(Training).statement, self.session.bind)

    def _get_new_data(self):
        # if empty filepath then return false
        if self.filepath == '':
            raise InvalidTrainingData('No file specified')

        # if the dataframe has description and category columns then return true
        df = pd.read_csv(self.filepath, index_col=False, encoding='utf-8-sig')
        df.columns = map(str.lower, df.columns)
        df.columns = map(str.strip, df.columns)
        if 'description' and 'category' in df.columns.values:
            df.columns = map(str.lower, df.columns)
            return df
        else:
            raise InvalidTrainingData(
                'Incorrect headers in specified file. File should only contain \'Description\' and \'Category\' headers.')
        raise InvalidTrainingData('Uncaught error with the supplied training data.')


class Categorise:

    def __init__(self, fp):
        self.filepath = fp

        # get data from specified filepath as dataframe
        try:
            test_data = self._get_test_data()
        except InvalidBankStatement as e:
            raise e

        # get trained svm model from expected location
        try:
            self.model = self._get_svm_model()
        except FileNotFoundError as e:
            raise e

        categories = self.model.predict(test_data.description)
        probabilities = self.model.predict_proba(test_data.description).max(axis=1)

        test_data['predicted_category'] = categories
        test_data['probability'] = probabilities

        self._save_results(test_data)

    def _save_results(self, d):
        while True:
            try:
                d.to_csv('data/test_results.csv', encoding='utf-8-sig')
                break
            except PermissionError as e:
                p = input(
                    'Error saving results. \'{}\' is already open, please close this file. Press enter to retry.'.format(
                        e.filename))

    def _get_test_data(self):
        # if empty filepath then raise error
        if self.filepath == '':
            raise InvalidBankStatement('No file specified')

        # if the dataframe has description then return df
        df = pd.read_csv(self.filepath, index_col=False, encoding='utf-8-sig')
        df.columns = map(str.lower, df.columns)
        df.columns = map(str.strip, df.columns)
        if 'description' in df.columns.values:
            df = df.dropna(subset=['description'])  # Drop rows with missing descriptions
            df['description'] = df['description'].astype(str)  # Ensure all are strings
            return df
        raise InvalidBankStatement(
            'Incorrect headers in specified file. File should contain a \'Description\' header.')

    def _get_svm_model(self):
        with open('./data/trained_svm.pkl', "rb") as input_file:
            m = pickle.load(input_file)
        if isinstance(m, Pipeline):
            return m
        else:
            raise InvalidModelError('The detected model is not compatible.')


def get_data_path():
    root = Tk()
    filepath = askopenfilename(initialdir="./data/", title="Select file", filetypes=(("CSV", "*.csv"),))
    root.destroy()
    return filepath


if __name__ == '__main__':
    # CLI usage
    from tkinter import Tk
    from tkinter.filedialog import askopenfilename

    def get_data_path():
        root = Tk()
        filepath = askopenfilename(initialdir="./data/", title="Select file", filetypes=(("CSV", "*.csv"),))
        root.destroy()
        return filepath

    while True:
        session_type = input('Select an option:\n'
                             '[1] - Categorise a bank statement (requires a trained categorisation model)\n'
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
            print('Invalid selection, please try again...\n\n')

