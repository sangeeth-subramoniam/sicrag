import psycopg2
import os

# Database connection details
DB_USER = os.getenv("SIC_DB_USER")
DB_PASS = os.getenv("SIC_DB_PASS")
DB_HOST = os.getenv("SIC_DB_HOST")
DB_PORT = 5432
DB_NAME = "postgres"


conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)


tablename = "rag_db"
file_table_name = "rag_file_db"
tag_table_name = "rag_tag_db"

def insert_tag(tagname,document_list):

    print('From insert_tag ' , tagname , document_list)
    
    cur = conn.cursor()


    def insert_tag_data(conn, tagname, document_list):
        
        # Looping though all the ids in the document list
        
        # document_names = []
        
        # for document_parent_name in document_list:

        #     parent_filename_search_query = f"""
        #         SELECT id,parent_filename
        #         FROM {file_table_name}
        #         WHERE parent_filename = '{document_parent_name}';
        #     """

        #     cur = conn.cursor()
        #     cur.execute(parent_filename_search_query)
        #     parent_filename_search_query_list = cur.fetchall()

        #     print(' the document parent filenames list is ' , parent_filename_search_query_list)

        #     for document_id,document_name in parent_filename_search_query_list:
        #         document_names.append(document_name)

        # print('The doc list size is {} and the items are {}'.format(len(document_names) , document_names) )
        
        for all_document_names in document_list:
            # Insert document into the table
            insert_query = f"""
                INSERT INTO {tag_table_name} (tag, parent_filename)
                VALUES (%s, %s)
                ON CONFLICT (tag, parent_filename) DO NOTHING;
            """
            with conn.cursor() as cur:
                cur.execute(insert_query, ( tagname, all_document_names))
                conn.commit()

            print('Tag {} for document id {} created successfully'.format(tagname , all_document_names))



    #テーブル作成 TABLE CREATION
    # create_table(conn)

    # # 行の追加 ROW INSERT

    insert_tag_data(conn, tagname,document_list)

    print('Tags Created Successfully')



def delete_tag(tagname,document_list):

    print('Enters delete tag with ' , tagname , document_list)

    for documents_parent_filename in document_list:

        delete_query = f"""
            DELETE FROM {tag_table_name}
            WHERE tag = '{tagname}'
            AND parent_filename = '{documents_parent_filename}';
        """
        with conn.cursor() as cur:
            cur.execute(delete_query)
            conn.commit()

    print('Deleted {} successfully'.format(document_list))
