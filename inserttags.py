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

def insert_tag(tagname,document_list):

    print('From insert_tag ' , tagname , document_list)
    
    cur = conn.cursor()


    def insert_tag_data(conn, tagname, document_list):
        
        # Looping though all the ids in the document list

        
        for document_id in document_list:
        
            # Insert document into the table
            insert_query = """
                INSERT INTO rag_vector_tag_db (tag, id)
                VALUES (%s, %s)
            """
            with conn.cursor() as cur:
                cur.execute(insert_query, (tagname, int(document_id)))
                conn.commit()

            print('Tag {} for document id {} created successfully'.format(tagname , document_id))



    #テーブル作成 TABLE CREATION
    # create_table(conn)

    # # 行の追加 ROW INSERT

    insert_tag_data(conn, tagname,document_list)

    print('Tags Created Successfully')



def delete_tag(tagname,document_list):

    print('Enters delete tag with ' , tagname , document_list)

    for documents_id in document_list:

        delete_query = """
            DELETE FROM rag_vector_tag_db
            WHERE id = %s;
        """
        with conn.cursor() as cur:
            cur.execute(delete_query, (documents_id,))
            conn.commit()

    print('Deleted {} successfully'.format(document_list))
