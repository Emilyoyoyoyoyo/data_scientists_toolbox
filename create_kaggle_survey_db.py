import string
import sqlite3
import pandas as pd

class CreateKaggleSurveyDB:
    def __init__(self):
        survey_years = [2020, 2021, 2022] #資料載入
        df_dict = dict() #tuple key: (年份, 問題描述 or 回答)
        #把問題跟回答分開存放在字典中
        for survey_year in survey_years:
            file_path = f"data/kaggle_survey_{survey_year}_responses.csv"
            #讀取回答
            df = pd.read_csv(file_path, low_memory=False, skiprows=[1]) #跳過檔案的第二行問題
            df = df.iloc[:, 1:] #row:column, 丟棄第一欄不重要資訊
            df_dict[survey_year, "responses"] = df #將整理後資料存入字典
            #讀取問題描述
            df = pd.read_csv(file_path, nrows=1) #只讀取第一列（問題描述)
            question_descriptions = df.values.ravel() #取value, 把值攤平成一維陣列
            question_descriptions = question_descriptions[1:] #跳過第一個欄位，保留問題描述
            df_dict[survey_year, "question_descriptions"] = question_descriptions #將tuple key問題描述存入字典
        self.survey_years = survey_years
        self.df_dict = df_dict

    def tidy_2020_2021_data(self, survey_year: int) -> tuple:
        #2020, 2021的題號欄位名稱，與2022不同(名稱沒有part)，分開處理
        # survey_year = 2020

        #查看題號的名稱差異（單選題Q1，多選題有Q19_Part_1 or Q26_A_Part_8）
        # column_names = df_dict[survey_year, "responses"].columns
        # for ele in column_names:
        #     print(ele)

        #題號，種類，敘述（單選or多選）
        #問題整理
        question_indexes, question_types, question_descriptions = [], [], []

        column_names = self.df_dict[survey_year, "responses"].columns #Q1, Q2...
        descriptions = self.df_dict[survey_year, "question_descriptions"]
        for column_name, question_description in zip(column_names, descriptions):
            column_name_split = column_name.split("_") #Q6_6
            question_description_split = question_description.split(" - ") 
            #透過Q題號的欄位長度判斷單選或多選題
            if len(column_name_split) == 1:
                question_index = column_name_split[0]
                question_indexes.append(question_index)
                question_types.append("Multiple choice")
                question_descriptions.append(question_description_split[0])
            #多選題
            else:
                #題目有A
                if column_name_split[1] in string.ascii_uppercase: #A
                    question_index = column_name_split[0] + column_name_split[1] #Q6_A
                    question_indexes.append(question_index)
                #其餘多選題
                else:
                    question_index = column_name_split[0]
                    question_indexes.append(question_index)
                question_types.append("Multiple selection")
                question_descriptions.append(question_description_split[0])
        # print(question_indexes)
        # print(question_types)
        # print(question_descriptions)

        question_df = pd.DataFrame()
        question_df["question_index"] = question_indexes
        question_df["question_type"] = question_types
        question_df["question_description"] = question_descriptions
        question_df["surveyed_in"] = survey_year
        # print(question_df) 用.count()，因為複選題會有重複的問題
        question_df = question_df.groupby(["question_index", "question_type", "question_description", "surveyed_in"]).count().reset_index()
        # print(question_df)

        #回覆整理
        response_df = self.df_dict[survey_year, "responses"]
        response_df.columns = question_indexes
        response_df_reset_index = response_df.reset_index() #加上受訪者的編號
        response_df_melted = pd.melt(response_df_reset_index, id_vars="index", var_name="question_index", value_name="response")
        # print(response_df_melted)
        response_df_melted["responded_in"] = survey_year
        response_df_melted = response_df_melted.rename(columns={"index": "respondent_id"})
        response_df_melted = response_df_melted.dropna().reset_index(drop=True)
        # print(response_df_melted)
        return question_df, response_df_melted
    
    def tidy_2022_data(self, survey_year: int) -> tuple:
        # 2022年資料整理
        survey_year = 2022
        question_indexes, question_types, question_descriptions = [], [], []
        column_names = self.df_dict[survey_year, "responses"].columns
        descriptions = self.df_dict[survey_year, "question_descriptions"]
        for column_name, question_description in zip(column_names, descriptions):
            column_name_split = column_name.split("_")
            question_description_split = question_description.split(" - ")
            if len(column_name_split) == 1:
                question_types.append("Multiple choice")
            else:
                question_types.append("Multiple selection")
            question_index = column_name_split[0]
            question_indexes.append(question_index)
            question_descriptions.append(question_description_split[0])
        # print(question_indexes)
        # print(question_types)
        # print(question_descriptions)

        # 題目整理
        question_df = pd.DataFrame()
        question_df["question_index"] = question_indexes
        question_df["question_type"] = question_types
        question_df["question_description"] = question_descriptions
        question_df["surveyed_in"] = survey_year
        question_df = question_df.groupby(["question_index", "question_type", "question_description", "surveyed_in"]).count().reset_index()
        # question_df.head()

        # 回覆整理
        response_df = self.df_dict[survey_year, "responses"]
        response_df.columns = question_indexes
        response_df_reset_index = response_df.reset_index()
        response_df_melted = pd.melt(response_df_reset_index, id_vars="index", var_name="question_index", value_name="response")
        response_df_melted["responded_in"] = survey_year
        response_df_melted = response_df_melted.rename(columns={"index": "respondent_id"})
        response_df_melted = response_df_melted.dropna().reset_index(drop=True)
        # print(response_df_melted)
        return question_df, response_df_melted
    
    def create_database(self):
        # 把3年的問題跟回答合併，6個df合併成一個df
        question_df = pd.DataFrame()
        response_df = pd.DataFrame()
        for survey_year in self.survey_years:
            if survey_year == 2022:
                q_df, r_df = self.tidy_2022_data(survey_year)
            else:
                q_df, r_df = self.tidy_2020_2021_data(survey_year)
            question_df = pd.concat([question_df, q_df], ignore_index=True)
            response_df = pd.concat([response_df, r_df], ignore_index=True)

        # 建立資料庫
        connection = sqlite3.connect("data/kaggle_survey.db")
        question_df.to_sql("questions", con=connection, if_exists="replace", index=False)
        response_df.to_sql("responses", con=connection, if_exists="replace", index=False)
        # 檢視表
        cur = connection.cursor()
        drop_view_sql = """
        DROP VIEW IF EXISTS aggregated_responses;
        """
        create_view_sql = """
        CREATE VIEW aggregated_responses AS
        SELECT questions.surveyed_in,
               questions.question_index,
               questions.question_type,
               questions.question_description,
               responses.response,
               COUNT(responses.respondent_id) AS response_count
          FROM responses
          JOIN questions
            ON responses.question_index = questions.question_index AND
               responses.responded_in = questions.surveyed_in
         GROUP BY questions.surveyed_in,
                  questions.question_index,
                  responses.response;
        """
        cur.execute(drop_view_sql)
        cur.execute(create_view_sql)
        connection.close()

create_kaggle_survey_db = CreateKaggleSurveyDB()
create_kaggle_survey_db.create_database()