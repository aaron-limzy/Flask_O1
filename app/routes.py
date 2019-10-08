from app import app, db, excel
from flask import render_template, flash, redirect, url_for, request, send_from_directory, jsonify, g, Markup
from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse
from app.forms import UploadForm, SymbolSwap, SymbolTotal, SymbolTotalTest, AddOffSet, MT5_Modify_Trades_Form, File_Form, LoginForm, CreateUserForm, noTrade_ChangeGroup_Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, HiddenField, FloatField, FormField
import pyexcel
from flask_table import create_table, Col
import urllib3
import decimal
import datetime
import os
import pandas as pd
import numpy as np
import requests
import json

from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, load_user, flask_users
from sqlalchemy import text
from Aaron_Lib import *

from .decorators import async
from io import StringIO


TIME_UPDATE_SLOW_MIN = 10
EMAIL_LIST_ALERT = ["aaron.lim@blackwellglobal.com"]
TELE_ID_MTLP_MISMATCH = "736426328:AAH90fQZfcovGB8iP617yOslnql5dFyu-M0"		# For Mismatch and LP Margin
TELE_ID_USDTWF_MISMATCH = "776609726:AAHVrhEffiJ4yWTn1nw0ZBcYttkyY0tuN0s"        # For USDTWF
TELE_CLIENT_ID = ["486797751"]        #Aaron's Telegram ID.

LP_MARGIN_ALERT_LEVEL = 20            # How much away from MC do we start making noise.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # To Display the warnings.


@app.route('/')
@app.route('/index')        # Indexpage. To show the generic page.
@login_required
def index():
    #return render_template("index.html", header="index page", description="Hello")
    return render_template("index.html", header="Risk Tool.", description="Welcome {}".format(current_user.id))

@app.route('/login', methods=['GET', 'POST'])       # Login Page. If user is login-ed, will re-direct to index.
def login():

    if current_user.is_authenticated:
        return redirect(url_for('index'))
    #else:
        #print("User is not authenticated. ")

    form = LoginForm()
    if form.validate_on_submit():
        user = load_user(username=form.username.data)
        if user is None or not user.check_password(form.password.data): # If Login error
            flash('Invalid username or password')
            return redirect(url_for('login'))
        else:
            flash('Login successful')
            login_user(user, remember=form.remember_me.data)

            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)

    return render_template('General_Form.html', title='Sign In',header="Sign In", form=form)


@app.route('/admin/create_user', methods=['GET', 'POST'])       # Login Page. If user is login-ed, will re-direct to index.
@login_required
def Create_User():

    form = CreateUserForm()
    if form.validate_on_submit():

        username = form.username.data
        email = form.email.data
        password = form.password.data
        admin_rights = 0

        user = flask_users.query.filter_by(username=username).first()
        if user is not None:
            flash("User {} is taken. Kindly choose another username.".format(username))  # Put a message out that there is some error.
        else:
            sql_insert = "INSERT INTO  aaron.`flask_login` (`username`, `email`, `password_hash`, `admin_rights`) VALUES" \
                " ('{}','{}','{}','{}')".format(username, email, User.hash_password(password=password), admin_rights)
            #print(sql_insert)
            raw_insert_result = db.engine.execute(sql_insert)

    return render_template('General_Form.html', title='Create User',header="Create User", form=form)


@app.route('/logout', methods=['GET', 'POST'])  # Will logout the user.
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/Dividend')
def Dividend():
    return render_template("base.html")


# @app.route('/upload')
# def upload_file2():
#     return '''
# <html>
#    <body>
#       <form action = "http://localhost:5000/uploader" method = "POST"
#          enctype = "multipart/form-data">
#          <input type = "file" name = "file" />
#          <input type = "submit"/>
#       </form>
#    </body>
# </html>
#     '''

#
# @app.route('/uploader', methods=['GET', 'POST'])
# def upload_file():
#     if request.method == 'POST':
#         f = request.files['file']
#         f.save(secure_filename(f.filename))
#         return 'file uploaded successfully'
#
#
# @app.route('/uploads/<filename>')
# def uploaded_file(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'],
#                                filename)


@app.route('/upload_LP_Swaps', methods=['GET', 'POST'])
def upload_excel():
    form = UploadForm()

    if request.method == 'POST' and form.validate_on_submit():

        record_dict = request.get_records(field_name='upload', name_columns_by_row=0)

        month_year = datetime.datetime.now().strftime('%b-%Y')
        month_year_folder = app.config["VANTAGE_UPLOAD_FOLDER"] + "/" + month_year

        filename = secure_filename(request.files['upload'].filename)

        filename_postfix_xlsx = Check_File_Exist(month_year_folder, ".".join(
            filename.split(".")[:-1]) + ".xlsx")  # Checks, Creates folders and return avaliable filename

        # Want to Let the users download the File..
        # return excel.make_response_from_records(record_dict, "xls", status=200, file_name=filename_without_postfix)

        pyexcel.save_as(records=record_dict, dest_file_name=filename_postfix_xlsx)

        column_name = []
        file_data = []
        for cc, record in enumerate(record_dict):
            if cc == 0:
                column_name = list(record_dict[cc].keys())
            buffer = {}
            print(record)
            for i, j in record.items():
                if i == "":
                    i = "Empty"
                buffer[i] = j
                print(i, j)
            file_data.append(buffer)

        T = create_table()
        table = T(file_data, classes=["table", "table-striped", "table-bordered", "table-hover"])
        if (len(file_data) > 0) and isinstance(file_data[0], dict):
            for c in file_data[0]:
                if c != "\n":
                    table.add_column(c, Col(c, th_html_attrs={"style": "background-color:#afcdff"}))
        #
        return render_template("upload_form.html", form=form, table=table)

    return render_template("upload_form.html", form=form)


@app.route('/test1', methods=['GET', 'POST'])
def retrieve_db_swaps():
    raw_result = db.engine.execute("select * from aaron.swap_bgi_vantage_coresymbol")
    result_data = raw_result.fetchall()
    result_col = raw_result.keys()
    result_colate = [dict(zip(result_col, a)) for a in result_data]

    T = create_table()
    table = T(result_colate, classes=["table", "table-striped", "table-bordered", "table-hover"])
    if (len(result_colate) > 0) and isinstance(result_colate[0], dict):
        for c in result_colate[0]:
            if c != "\n":
                table.add_column(c, Col(c, th_html_attrs={"style": "background-color:#afcdff"}))
    return render_template("Swap_Sql.html", table=table)


@app.route('/upload_swap', methods=['GET', 'POST'])
def retrieve_db_swaps2():
    form = UploadForm()

    if request.method == 'POST' and form.validate_on_submit():

        record_dict = request.get_records(field_name='upload', name_columns_by_row=0)
        #record_dict = request.get_records(field_name='upload')
        month_year = datetime.now().strftime('%b-%Y')
        month_year_folder = app.config["VANTAGE_UPLOAD_FOLDER"] + "/" + month_year

        filename = secure_filename(request.files['upload'].filename)

        filename_postfix_xlsx = Check_File_Exist(month_year_folder, ".".join(
            filename.split(".")[:-1]) + ".xlsx")  # Checks, Creates folders and return avaliable filename

        # Want to Let the users download the File..
        # return excel.make_response_from_records(record_dict, "xls", status=200, file_name=filename_without_postfix)

        # pyexcel.save_as(records=record_dict, dest_file_name=filename_postfix_xlsx)

        column_name = []
        file_data = []
        for cc, record in enumerate(record_dict):
            if cc == 0:
                column_name = list(record_dict[cc].keys())
            buffer = {}
            #print(record)
            for i, j in record.items():
                if i == "":
                    i = "Empty"
                buffer[str(i).strip()] = str(j).strip()
                print(i, j)
            file_data.append(buffer)

        raw_result = db.engine.execute("\
            select `BGI_CORE`.`BGI_CORE_SYMBOL`,`BGI_VANTAGE`.`VANTAGE_CORE_SYMBOL`,`BGI_CORE`.`BGI_TYPE` , \
            `BGI_CORE`.`BGI_CONTRACT_SIZE` , `BGI_CORE`.`BGI_DIGITS` , `VANTAGE_CORE`.`VANTAGE_DIGITS`,`VANTAGE_CORE`.`VANTAGE_CONTRACT_SIZE`, \
            `BGI_CORE`.`BGI_POSITIVE_MARKUP`, `BGI_CORE`.`BGI_NEGATIVE_MARKUP`, `BGI_CORE`.currency, \
            `BGI_FORCED`.`FORCED_BGI_LONG`, `BGI_FORCED`.`FORCED_BGI_SHORT`,  \
            `BGI_FORCED_INSTI`.`BGI_INSTI_FORCED_LONG`,`BGI_FORCED_INSTI`.`BGI_INSTI_FORCED_SHORT` \
            from \
            (Select core_symbol as `BGI_CORE_SYMBOL`, contract_size as `BGI_CONTRACT_SIZE`, digits as `BGI_DIGITS`,  \
            type as `BGI_TYPE`, positive_markup as `BGI_POSITIVE_MARKUP`, negative_markup as `BGI_NEGATIVE_MARKUP` ,currency \
            from swap_bgicoresymbol) as `BGI_CORE` \
            LEFT JOIN \
            (Select bgi_coresymbol as `BGI_CORESYMBOL`, vantage_coresymbol as `VANTAGE_CORE_SYMBOL`  \
            from aaron.swap_bgi_vantage_coresymbol) as `BGI_VANTAGE` on BGI_CORE.BGI_CORE_SYMBOL = BGI_VANTAGE.BGI_CORESYMBOL \
            LEFT JOIN \
            (Select core_symbol as `VANTAGE_CORESYMBOL`,contract_size as `VANTAGE_CONTRACT_SIZE`, digits as `VANTAGE_DIGITS`  \
            from aaron.swap_vantagecoresymbol) as `VANTAGE_CORE` on `VANTAGE_CORE`.`VANTAGE_CORESYMBOL` = `BGI_VANTAGE`.`VANTAGE_CORE_SYMBOL` \
            LEFT JOIN \
            (Select core_symbol as `FORCED_BGI_CORESYMBOL`,`long` as `FORCED_BGI_LONG`, short as `FORCED_BGI_SHORT`  \
            from aaron.swap_bgiforcedswap) as `BGI_FORCED` on BGI_CORE.BGI_CORE_SYMBOL = BGI_FORCED.FORCED_BGI_CORESYMBOL \
            LEFT JOIN \
            (Select core_symbol as `BGI_INSTI_FORCED_CORESYMBOL`, `long` as `BGI_INSTI_FORCED_LONG`, short as `BGI_INSTI_FORCED_SHORT`  \
            from aaron.swap_bgiforcedswap_insti) as `BGI_FORCED_INSTI` on `BGI_CORE`.BGI_CORE_SYMBOL = `BGI_FORCED_INSTI`.BGI_INSTI_FORCED_CORESYMBOL \
            order by FIELD(`BGI_CORE`.BGI_TYPE, 'FX','Exotic Pairs', 'PM', 'CFD'), BGI_CORE.BGI_CORE_SYMBOL \
        ")

        result_data = raw_result.fetchall()
        result_col = raw_result.keys()
        result_col_no_duplicate = []
        for a in result_col:
            if not a in result_col_no_duplicate:
                result_col_no_duplicate.append(a)
            else:
                result_col_no_duplicate.append(str(a)+"_1")

        collate = [dict(zip(result_col_no_duplicate, a)) for a in result_data]

        # Calculate the Markup, as well as acount for the difference in Digits.
        for i, c in enumerate(collate):     # By Per Row
            collate[i]["SWAP_UPLOAD_LONG"] = ""         # We want to add the following..
            collate[i]["SWAP_UPLOAD_LONG_MARKUP"] = ""
            collate[i]["SWAP_UPLOAD_SHORT"] = ""
            collate[i]["SWAP_UPLOAD_SHORT_MARKUP"] = ""

            bgi_digit_difference = 0        # Sets as 0 for default.
            if ("BGI_DIGITS"  in collate[i]) and ("VANTAGE_DIGITS" in collate[i]) and (collate[i]["BGI_DIGITS"] != None) and (collate[i]["VANTAGE_DIGITS"] != None):      # Need to calculate the Digit Difference.
                bgi_digit_difference = int(collate[i]["BGI_DIGITS"]) - int(collate[i]["VANTAGE_DIGITS"])



            #print(str(collate[i]['VANTAGE_CORE_SYMBOL']))

            # Retail_Sheet.Cells(i, 2).Value = Find_Retail(Core_Symbol_BGI, 2, Cell_Color) * (10 ^ (Symbol_BGI_Digits - Symbol_Vantage_Digits))



            for j, d in enumerate(file_data):
                if 'VANTAGE_CORE_SYMBOL' in collate[i] and \
                        len(list(d.keys())) >= 1 and \
                        str(collate[i]['VANTAGE_CORE_SYMBOL']).strip() == d[list(d.keys())[0]]:

                    d_key = [str(a).strip() for a in list(d.keys())]        # Get the keys for the Uploaded data.



                    for ij, coll in enumerate(d_key):
                        if "buy" in str(coll).lower() or "long" in str(coll).lower():   # Search for buy or long
                            # Need to check if can be float.
                            collate_keys = list(collate[i].keys())
                            if "BGI_POSITIVE_MARKUP" in collate_keys and "BGI_NEGATIVE_MARKUP" in collate_keys and Check_Float(d[coll]):         # If posive, markup with positive markup. if negative, use negative markup.
                                val = str(round(markup_swaps(float(str(d[coll])), collate[i]["BGI_POSITIVE_MARKUP"], collate[i]["BGI_NEGATIVE_MARKUP"])  * (10 ** bgi_digit_difference),4))  # Does the Digit Conversion here.
                            else:
                                val = ""
                                flash("Unable to calculate markup prices for {}".format(collate[i]["BGI_CORE_SYMBOL"]))     # Put a message out that there is some error.

                            collate[i]["SWAP_UPLOAD_LONG"] = str(d[coll])
                            collate[i]["SWAP_UPLOAD_LONG_MARKUP"] = val


                        if "sell" in str(coll).lower() or "short" in str(coll).lower(): # Search for sell or short in the colum names.

                            # Need to check if can be float.
                            collate_keys = list(collate[i].keys())
                            if "BGI_POSITIVE_MARKUP" in collate_keys and "BGI_NEGATIVE_MARKUP" in collate_keys and Check_Float(d[coll]):    # If posive, markup with positive markup. if negative, use negative markup.
                                val = str( round(markup_swaps(float(str(d[coll])), collate[i]["BGI_POSITIVE_MARKUP"], collate[i]["BGI_NEGATIVE_MARKUP"]) * (10 ** bgi_digit_difference)  ,4) ) # Does the Digit Conversion here.
                            else:
                                val = ""

                            collate[i]["SWAP_UPLOAD_SHORT"] = str(d[coll])
                            collate[i]["SWAP_UPLOAD_SHORT_MARKUP"] = val
                    # print(d_key[0])
                    break


        # To Create the BGI Swaps.
        bgi_long_swap_column = ["FORCED_BGI_LONG", "SWAP_UPLOAD_LONG_MARKUP"]       # To get the swap values in that order.
        bgi_short_swap_column = ["FORCED_BGI_SHORT", "SWAP_UPLOAD_SHORT_MARKUP"]    # If there are forced swaps, get forced first.

        bgi_insti_long_swap_column = ["FORCED_BGI_LONG", "BGI_INSTI_FORCED_LONG", "SWAP_UPLOAD_LONG_MARKUP"]    # If there are forced, if there are any Insti Forced, then the markup values.
        bgi_insti_short_swap_column = ["FORCED_BGI_SHORT", "BGI_INSTI_FORCED_SHORT", "SWAP_UPLOAD_SHORT_MARKUP"]


        bgi_swaps_retail = []
        bgi_swaps_insti = []
        for c in collate:
            buffer_retail = {"SYMBOL": c["BGI_CORE_SYMBOL"], "LONG" : "", "SHORT" : ""}
            buffer_insti ={"SYMBOL": c["BGI_CORE_SYMBOL"], "LONG" : "", "SHORT" : ""}

            for l in bgi_long_swap_column:      # Going by Precedence.
                if l in c and c[l] != None:
                    buffer_retail["LONG"] = c[l]
                    break
            for s in bgi_short_swap_column:      # Going by Precedence.
                if s in c and c[s] != None:
                    buffer_retail["SHORT"] = c[s]
                    break
            for li in bgi_insti_long_swap_column:      # Going by Precedence.
                if li in c and c[li] != None:
                    buffer_insti["LONG"] = c[li]
                    break
            for si in bgi_insti_short_swap_column:      # Going by Precedence.
                if si in c and c[si] != None:
                    buffer_insti["SHORT"] = c[si]
                    break

            if buffer_retail["LONG"] == "" or buffer_retail["SHORT"] == "" or buffer_insti["LONG"] == "" or buffer_insti["SHORT"] == "" :
                flash("{} has no Swaps.".format(c["BGI_CORE_SYMBOL"]))  # Flash out if there are no swaps found.

            bgi_swaps_retail.append(buffer_retail)
            bgi_swaps_insti.append(buffer_insti)


        collate_table = [dict(zip([str(a).replace("_", " ") for a in c.keys()], c.values())) \
                         for c in collate]


        table = create_table_fun(collate_table)

        table_bgi_swaps_retail = create_table_fun(bgi_swaps_retail)
        table_bgi_swaps_insti = create_table_fun(bgi_swaps_insti)



        return render_template("upload_form.html", table=table, form=form, table_bgi_swaps_retail=table_bgi_swaps_retail, table_bgi_swaps_insti=table_bgi_swaps_insti)

    return render_template("upload_form.html", form=form)


@app.route('/upload_swap3', methods=['GET', 'POST'])
def retrieve_db_swaps3():
    form = UploadForm()

    if request.method == 'POST' and form.validate_on_submit():

        # Get the file details as Records.
        record_dict = request.get_records(field_name='upload', name_columns_by_row=0)

        # ------------------ Dataframe of the data from CSV File. -----------------
        df_csv = pd.DataFrame(record_dict)

        uploaded_excel_data = df_csv.fillna("-").rename(columns=dict(zip(df_csv.columns,[a.replace("_","\n") for a in df_csv.columns]))).to_html(classes="table table-striped table-bordered table-hover table-condensed", index=False)


        for i in df_csv.columns:  # Want to see which is Long and which is Short.
            if "core symbol" in i.lower():
                df_csv.rename(columns={i: "VANTAGE_CORE_SYMBOL"}, inplace=True) # Need to rename "Core symbol" to note that its from vantage.
            if "long" in i.lower():
                df_csv.rename(columns={i: "CSV_LONG"}, inplace=True)
            if "short" in i.lower():
                df_csv.rename(columns={i: "CSV_SHORT"}, inplace=True)


        raw_result = db.engine.execute("\
            select `BGI_CORE`.`BGI_CORE_SYMBOL`,`BGI_VANTAGE`.`VANTAGE_CORE_SYMBOL`,`BGI_CORE`.`BGI_TYPE` , \
            `BGI_CORE`.`BGI_CONTRACT_SIZE` , `BGI_CORE`.`BGI_DIGITS` , `VANTAGE_CORE`.`VANTAGE_DIGITS`,`VANTAGE_CORE`.`VANTAGE_CONTRACT_SIZE`, \
            `BGI_CORE`.`BGI_POSITIVE_MARKUP`, `BGI_CORE`.`BGI_NEGATIVE_MARKUP`, `BGI_CORE`.currency, \
            `BGI_FORCED`.`FORCED_BGI_LONG`, `BGI_FORCED`.`FORCED_BGI_SHORT`,  \
            `BGI_FORCED_INSTI`.`BGI_INSTI_FORCED_LONG`,`BGI_FORCED_INSTI`.`BGI_INSTI_FORCED_SHORT` \
            from \
            (Select core_symbol as `BGI_CORE_SYMBOL`, contract_size as `BGI_CONTRACT_SIZE`, digits as `BGI_DIGITS`,  \
            type as `BGI_TYPE`, positive_markup as `BGI_POSITIVE_MARKUP`, negative_markup as `BGI_NEGATIVE_MARKUP` ,currency \
            from swap_bgicoresymbol) as `BGI_CORE` \
            LEFT JOIN \
            (Select bgi_coresymbol as `BGI_CORESYMBOL`, vantage_coresymbol as `VANTAGE_CORE_SYMBOL`  \
            from aaron.swap_bgi_vantage_coresymbol) as `BGI_VANTAGE` on BGI_CORE.BGI_CORE_SYMBOL = BGI_VANTAGE.BGI_CORESYMBOL \
            LEFT JOIN \
            (Select core_symbol as `VANTAGE_CORESYMBOL`,contract_size as `VANTAGE_CONTRACT_SIZE`, digits as `VANTAGE_DIGITS`  \
            from aaron.swap_vantagecoresymbol) as `VANTAGE_CORE` on `VANTAGE_CORE`.`VANTAGE_CORESYMBOL` = `BGI_VANTAGE`.`VANTAGE_CORE_SYMBOL` \
            LEFT JOIN \
            (Select core_symbol as `FORCED_BGI_CORESYMBOL`,`long` as `FORCED_BGI_LONG`, short as `FORCED_BGI_SHORT`  \
            from aaron.swap_bgiforcedswap) as `BGI_FORCED` on BGI_CORE.BGI_CORE_SYMBOL = BGI_FORCED.FORCED_BGI_CORESYMBOL \
            LEFT JOIN \
            (Select core_symbol as `BGI_INSTI_FORCED_CORESYMBOL`, `long` as `BGI_INSTI_FORCED_LONG`, short as `BGI_INSTI_FORCED_SHORT`  \
            from aaron.swap_bgiforcedswap_insti) as `BGI_FORCED_INSTI` on `BGI_CORE`.BGI_CORE_SYMBOL = `BGI_FORCED_INSTI`.BGI_INSTI_FORCED_CORESYMBOL \
            order by FIELD(`BGI_CORE`.BGI_TYPE, 'FX','Exotic Pairs', 'PM', 'CFD'), BGI_CORE.BGI_CORE_SYMBOL \
        ")

        result_data = raw_result.fetchall()
        result_col = raw_result.keys()
        result_col_no_duplicate = []
        for a in result_col:
            if not a in result_col_no_duplicate:
                result_col_no_duplicate.append(a)
            else:
                result_col_no_duplicate.append(str(a)+"_1")

        # Pandas data frame for the SQL return for the Symbol details.
        df_sym_details = pd.DataFrame(data=result_data, columns=result_col_no_duplicate)
        df_sym_details["DIGIT_DIFFERENCE"] = df_sym_details['BGI_DIGITS'] - df_sym_details['VANTAGE_DIGITS']    # Want to calculate the Digit Difference.


        # ---------------------------- Time to merge the 2 Data Frames. ---------------------------------------------
        combine_df = df_sym_details.merge(df_csv, on=["VANTAGE_CORE_SYMBOL"], how="outer")
        combine_df = combine_df[pd.notnull(combine_df["BGI_CORE_SYMBOL"])]

        # Need to Flip LONG
        combine_df["CSV_LONG"] = combine_df[ "CSV_LONG"] * -1  # Vantage sending us Positive = Charged. We need to flip  LONG
        # Need to correct the number of digits.
        if "CSV_LONG" in combine_df.columns:
            combine_df["CSV_LONG_CORRECT_DIGITS"] = combine_df["CSV_LONG"] * (10 ** combine_df["DIGIT_DIFFERENCE"])
        if "CSV_SHORT" in combine_df.columns:
            combine_df["CSV_SHORT_CORRECT_DIGITS"] = combine_df["CSV_SHORT"] * (10 ** combine_df["DIGIT_DIFFERENCE"])

        # Want to multiply by the correct markup for each. Want to give less, take more.
        # Long
        combine_df["CSV_LONG_CORRECT_DIGITS_MARKUP"] = np.where(combine_df["CSV_LONG_CORRECT_DIGITS"] > 0, round(
            combine_df["CSV_LONG_CORRECT_DIGITS"] * (1 - (combine_df["BGI_POSITIVE_MARKUP"] / 100)), 3), round(
            combine_df["CSV_LONG_CORRECT_DIGITS"] * (1 + (combine_df["BGI_NEGATIVE_MARKUP"] / 100)), 3))
        # Short
        combine_df["CSV_SHORT_CORRECT_DIGITS_MARKUP"] = np.where(combine_df["CSV_SHORT_CORRECT_DIGITS"] > 0, round(
            combine_df["CSV_SHORT_CORRECT_DIGITS"] * (1 - (combine_df["BGI_POSITIVE_MARKUP"] / 100)), 3), round(
            combine_df["CSV_SHORT_CORRECT_DIGITS"] * (1 + (combine_df["BGI_NEGATIVE_MARKUP"] / 100)), 3))

        # The Data Frame used for the Building of the CSV File.
        build_bgi_swap_df = combine_df[
            ["BGI_CORE_SYMBOL", "VANTAGE_CORE_SYMBOL", "BGI_POSITIVE_MARKUP", "BGI_NEGATIVE_MARKUP", "FORCED_BGI_LONG",
             "FORCED_BGI_SHORT", "BGI_INSTI_FORCED_LONG", "BGI_INSTI_FORCED_SHORT", "CSV_LONG_CORRECT_DIGITS_MARKUP",
             "CSV_SHORT_CORRECT_DIGITS_MARKUP", "BGI_TYPE"]]

        # Want to get either the Forced Swaps, if not, Get the "Vantage corrected digit markup" swaps
        build_bgi_swap_df.loc[:, "LONG"] = np.where(pd.notnull(build_bgi_swap_df["FORCED_BGI_LONG"]),
                                                    round(build_bgi_swap_df["FORCED_BGI_LONG"], 3), np.where(
                pd.notnull(build_bgi_swap_df["CSV_LONG_CORRECT_DIGITS_MARKUP"]),
                round(build_bgi_swap_df["CSV_LONG_CORRECT_DIGITS_MARKUP"], 3),
                build_bgi_swap_df["CSV_LONG_CORRECT_DIGITS_MARKUP"]))
        build_bgi_swap_df.loc[:, "SHORT"] = np.where(pd.notnull(build_bgi_swap_df["FORCED_BGI_SHORT"]),
                                                     round(build_bgi_swap_df["FORCED_BGI_SHORT"], 3), np.where(
                pd.notnull(build_bgi_swap_df["CSV_SHORT_CORRECT_DIGITS_MARKUP"]),
                round(build_bgi_swap_df["CSV_SHORT_CORRECT_DIGITS_MARKUP"], 3),
                build_bgi_swap_df["CSV_SHORT_CORRECT_DIGITS_MARKUP"]))

        # For Insti, we want to check BGI_FORCED first, if null, check BGI_INSTI_FORCED. If not, use vantage digit change markup swap.
        build_bgi_swap_df.loc[:, "INSTI_LONG"] = np.where(pd.notnull(build_bgi_swap_df["FORCED_BGI_LONG"]), round(build_bgi_swap_df["FORCED_BGI_LONG"], 3), \
                                                          np.where( pd.notnull(build_bgi_swap_df["BGI_INSTI_FORCED_LONG"]), round(build_bgi_swap_df["BGI_INSTI_FORCED_LONG"], 3), \
                                                              np.where(pd.notnull( build_bgi_swap_df["CSV_LONG_CORRECT_DIGITS_MARKUP"]), round(build_bgi_swap_df[ "CSV_LONG_CORRECT_DIGITS_MARKUP"], 3), \
                                                                       build_bgi_swap_df["CSV_LONG_CORRECT_DIGITS_MARKUP"])))


        build_bgi_swap_df.loc[:, "INSTI_SHORT"] = np.where(pd.notnull(build_bgi_swap_df["FORCED_BGI_SHORT"]), round(build_bgi_swap_df["FORCED_BGI_SHORT"], 3), \
                                                           np.where( pd.notnull(build_bgi_swap_df["BGI_INSTI_FORCED_SHORT"]), round(build_bgi_swap_df["BGI_INSTI_FORCED_SHORT"], 3), \
                                                               np.where(pd.notnull(build_bgi_swap_df["CSV_SHORT_CORRECT_DIGITS_MARKUP"]), round(build_bgi_swap_df["CSV_SHORT_CORRECT_DIGITS_MARKUP"], 3), \
                                                                        build_bgi_swap_df["CSV_SHORT_CORRECT_DIGITS_MARKUP"])))

        #Want to find out which of the symbols still have NULL.

        Swap_Error = build_bgi_swap_df[pd.isnull(build_bgi_swap_df["LONG"]) | pd.isnull(build_bgi_swap_df["SHORT"])]
        if len(Swap_Error) != 0:
            for a in Swap_Error["BGI_CORE_SYMBOL"]:
                flash("{} has swap errors. Swap is null.".format(a))

        # Minimising the data frame. Want to compare with median of last 15 days.
        build_bgi_swap_df_show = build_bgi_swap_df[["BGI_CORE_SYMBOL", "LONG", "SHORT", "INSTI_LONG", "INSTI_SHORT"]]   #Data Frame

        raw_result2 = db.engine.execute("SELECT * FROM test.bgi_swaps where date > CURDATE()-15")

        result_data2 = raw_result2.fetchall()
        result_col2 = raw_result2.keys()


        cfd_swaps = pd.DataFrame(data=result_data2, columns=result_col2)
        cfd_swaps.loc[:, "bgi_long"] = pd.to_numeric(cfd_swaps["bgi_long"])
        cfd_swaps.loc[:, "bgi_short"] = pd.to_numeric(cfd_swaps["bgi_short"])
        cfd_swaps.rename(columns={"Core_Symbol": "BGI_CORE_SYMBOL", "bgi_long":"BGI_LONG_AVERAGE", "bgi_short":"BGI_SHORT_AVERAGE"}, inplace=True)  #Rename for easy join.
        cfd_swaps_median = cfd_swaps.groupby("BGI_CORE_SYMBOL").median()
        combine_average_df = build_bgi_swap_df_show.join(cfd_swaps_median, on=["BGI_CORE_SYMBOL"])

        #combine_average_df[]

        # Data that we want to show.

        #table_bgi_swaps_retail = combine_average_df.fillna("-").rename(columns=dict(zip(combine_average_df.columns,[a.replace("_","\n") for a in combine_average_df.columns]))).to_html(classes="table table-striped table-bordered table-hover table-condensed", index=False)
        table_bgi_swaps_retail = combine_average_df.fillna("-").rename(columns=dict(zip(combine_average_df.columns,[a.replace("_","\n") for a in combine_average_df.columns]))).style.hide_index().applymap(color_negative_red, subset=["LONG","SHORT"]).set_table_attributes('class="table table-striped table-bordered table-hover table-condensed"').render()

        table_bgi_swaps_insti = ""


        table = combine_df.fillna("-").rename(columns=dict(zip(combine_df.columns,[a.replace("_","\n") for a in combine_df.columns]))).to_html(classes="table table-striped table-bordered table-hover table-condensed", index=False)

        return render_template("upload_form2.html", table=table, form=form, table_bgi_swaps_retail=table_bgi_swaps_retail, table_bgi_swaps_insti=table_bgi_swaps_insti, uploaded_excel_data = uploaded_excel_data)

    return render_template("upload_form.html", form=form)



def color_negative_red(value):
  """
  Colors elements in a dateframe
  green if positive and red if
  negative. Does not color NaN
  values.
  """

  if value < 0:
    color = 'red'
  elif value > 0:
    color = 'green'
  else:
    color = 'black'

  return 'color: %s' % color




@app.route('/add_offset', methods=['GET', 'POST'])      #Want to add an offset to the ABook page.
@login_required
def add_off_set():
    form = AddOffSet()
    if request.method == 'POST' and form.validate_on_submit():
        symbol = form.Symbol.data       #Get the Data.
        offset = form.Offset.data
        ticket = form.Ticket.data
        lp = form.LP.data
        comment = form.Comment.data
        sql_insert = "INSERT INTO  test.`offset_live_trades` (`symbol`, `ticket`, `lots`, `Comment`, `datetime`, `lp`) VALUES" \
            " ('{}','{}','{}','{}',NOW(),'{}' )".format(symbol, ticket, offset, comment, lp)
        #print(sql_insert)
        raw_insert_result = db.engine.execute(sql_insert)

    raw_result = db.engine.execute("SELECT SYMBOL, SUM(LOTS) as 'BGI Lots' FROM test.`offset_live_trades` GROUP BY SYMBOL ORDER BY `BGI Lots` DESC")
    result_data = raw_result.fetchall()
    result_col = raw_result.keys()
    collate = [dict(zip(result_col, a)) for a in result_data]
    table = create_table_fun(collate)
    title = "Add offset"
    header="Adding A-Book Offset"
    description = "Adding to the off set table, to manage our position for A book end for tally sake."

    return render_template("General_Form.html", form=form, table=table, title=title, header=header,description=description)



# Want to change user group should they have no trades.
# ie: From B to A or A to B.
@app.route('/NoOpenTrades_ChangeGroup', methods=['GET', 'POST'])
@login_required
def NoOpenTrades_ChangeGroup():
    #TODO: Need to check insert return.


    form = noTrade_ChangeGroup_Form()

    title = "Change Group[No Open Trades]."
    header = "Change Group[No Open Trades]."
    description = "Running only on Live 1 and Live 3.<br>Will change the client's group based on data from SQL table: test.changed_group_opencheck<br>When CHANGED = 0."

    if request.method == 'POST' and form.validate_on_submit():
        Live = form.Live.data       #Get the Data.
        Login = form.Login.data
        Current_Group = form.Current_Group.data
        New_Group = form.New_Group.data
        sql_insert = "INSERT INTO  test.`changed_group_opencheck` (`Live`, `login`, `current_group`, `New_Group`, `Changed`, `Time_Changed`) VALUES" \
             " ({live},{login},'{current_group}','{new_group}',{changed},now() )".format(live=Live,login=Login, current_group=Current_Group,new_group=New_Group,changed=0)
        print(sql_insert)
        raw_insert_result = db.engine.execute(sql_insert)

    # elif request.method == 'POST' and form.validate_on_submit() == False:
    #     flash('Invalid Form Entry')


    return render_template("Change_USer_Group.html", form=form,title=title, header=header, description=Markup(description))


@app.route('/NoOpenTrades_ChangeGroup_ajax', methods=['GET', 'POST'])
@login_required
def NoOpenTrades_ChangeGroup_ajax():
    # TODO: Check if user exist first.

    live_to_run = [1, 3]  # Only want to run this on Live 1 and 3.

    # Raw SQL Statment. Will have to use .format(live=1) for example.
    raw_sql_statement = """SELECT mt4_users.LOGIN, X.LIVE, X.CURRENT_GROUP as `CURRENT_GROUP[CHECK]`, X.NEW_GROUP, mt4_users.`GROUP` as USER_CURRENT_GROUP,
    					CASE WHEN mt4_users.`GROUP` = X.CURRENT_GROUP THEN 'Yes' ELSE 'No' END as CURRENT_GROUP_TALLY, 
    					CASE WHEN X.NEW_GROUP IN (SELECT `GROUP` FROM Live{live}.mt4_groups WHERE `GROUP` LIKE X.NEW_GROUP) THEN 'Yes' ELSE 'No' END as NEW_GROUP_FOUND, 
    					COALESCE((SELECT count(*) FROM live{live}.mt4_trades WHERE mt4_trades.LOGIN = X.LOGIN AND CLOSE_TIME = "1970-01-01 00:00:00" GROUP BY mt4_trades.LOGIN),0) as OPEN_TRADE_COUNT
    			FROM Live{live}.mt4_users,(SELECT LIVE,LOGIN,CURRENT_GROUP,NEW_GROUP FROM test.changed_group_opencheck WHERE LIVE = '{live}' and `CHANGED` = 0 ) X
    			WHERE mt4_users.`ENABLE` = 1 and mt4_users.LOGIN = X.LOGIN """

    raw_sql_statement = raw_sql_statement.replace("\t", " ").replace("\n", " ")
    # construct the SQL Statment
    sql_query_statement = " UNION ".join([raw_sql_statement.format(live=l) for l in live_to_run])
    sql_result = Query_SQL_db_engine(sql_query_statement)  # Query SQL

    return_val = {}     #Initialise.

    C_Return = {}   # The returns from C++
    C_Return[0] = "User Changed"
    C_Return[-1] = "C++ ERROR: No Connection"
    C_Return[-2] = "C++ ERROR: New Group Not Found"
    C_Return[-3] = "C++ ERROR: User Current Group mismatched"
    C_Return[-4] = "C++ ERROR: Unknown Error"
    C_Return[-5] = "C++ ERROR: Open Trades"
    C_Return[-6] = "C++ ERROR: User Not Found!"
    C_Return[-10] = "C++ ERROR: Param Error"


    # Need to update Run time on SQL Update table.
    async_Update_Runtime("ChangeGroup_NoOpenTrades")

    if len(sql_result) == 0:    # If there are nothing to be changed.
        return_val = {"All": [{"Comment":"Login awaiting change: 0", "Last Query time": "{}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}]}
        return json.dumps(return_val)

    success_result = []
    success_listdict = []
    for i,d in enumerate(sql_result):
        comment =""
        error_flag = 0

        if not ("CURRENT_GROUP_TALLY" in d and d["CURRENT_GROUP_TALLY"].find("Yes") >=0):
            comment += "Current group doesn't match. "
            error_flag += 1
        if not ("NEW_GROUP_FOUND" in d and d["NEW_GROUP_FOUND"].find("Yes") >=0):
            comment += "New group not found. "
            error_flag += 1
        if ("OPEN_TRADE_COUNT" in d and d["OPEN_TRADE_COUNT"] == 0):
            if error_flag == 0: # No obvious error from the SQL Return Code.

                server = d["LIVE"] if "LIVE" in d else False
                login = d["LOGIN"] if "LOGIN" in d else False
                previous_group = d["USER_CURRENT_GROUP"] if "USER_CURRENT_GROUP" in d else False
                new_group = d["NEW_GROUP"] if "NEW_GROUP" in d else False
                if all([server,login,previous_group, new_group]):     # Need to run C++ Should there be anything to change.
                    # #(C_Return_Val, output, err)
                    #c_run_return= [0,0,0]   # Artificial Results.
                    c_run_return = Run_C_Prog("app" + url_for('static', filename='Exec/Change_User.exe') + " {server} {login} {previous_group} {new_group}".format(
                        server=server,login=login,previous_group=previous_group,new_group=new_group))


                    comment += C_Return[c_run_return[0]]
                    if c_run_return[0] == 0:    # If C++ Returns okay.
                        success_result.append((server, login, previous_group, new_group))
                        # Want to add into a list of dict. Want to change the _ of Keys to " " Spaces.
                        changed_user_buffer = dict(zip([k.replace("_", " ") for k in list(d.keys())], d.values()))
                        changed_user_buffer["UPDATED TIME"] = time_now()    # Want to add in the SGT that it was changed.
                        success_listdict.append(changed_user_buffer)
                else:
                    comment += "SQL Return Error. [LIVE, LOGIN, USER_CURRENT_GROUP, NEW_GROUP]"

        else:   # There are open trades. Cannot Change.
            comment += "Open trades found."
        sql_result[i]["Comment"] = comment if error_flag == 0 else "ERROR: {}".format(comment)

    if len(success_result) > 0:  # For those that are changed, We want to save it in SQL.
        # Want to get the WHERE statements for each.
        sql_where_statement = " OR ".join(["(LOGIN = {login} and LIVE = {server} and CURRENT_GROUP = '{previous_group}' and NEW_GROUP = '{new_group}') ".format(
            server=server, login=login,previous_group=previous_group,new_group=new_group) for (server, login, previous_group, new_group) in success_result])
        #print(sql_where_statement)

        # Construct the SQL Statement
        sql_update_statement = """UPDATE test.changed_group_opencheck set `CHANGED` = 1, TIME_CHANGED = now() where (	"""
        sql_update_statement += sql_where_statement
        sql_update_statement += """ ) and `CHANGED` = 0 and TIME_CHANGED = '1970-01-01 00:00:00'"""
        sql_update_statement = text(sql_update_statement)   # To SQL Friendly Text.
        raw_insert_result = db.engine.execute(sql_update_statement) # TO SQL


    val = [list(a.values()) for a in sql_result]
    key = list(sql_result[0].keys())
    key = [k.replace("_"," ") for k in key]     # Want to space things out instead of _
    return_val = {"All": [dict(zip(key,v)) for v in val], "Changed": success_listdict}




    #table = create_table_fun(sql_result)
    return json.dumps(return_val)


# Want to change user group should they have no trades.
# ie: From B to A or A to B.
@app.route('/Risk_autocut', methods=['GET', 'POST'])
@login_required
def Risk_autocut():
    #TODO: Need to check insert return.


    form = noTrade_ChangeGroup_Form()

    title = "Change Group[No Open Trades]."
    header = "Change Group[No Open Trades]."
    description = "Running only on Live 1 and Live 3.<br>Will change the client's group based on data from SQL table: test.changed_group_opencheck<br>When CHANGED = 0."

    if request.method == 'POST' and form.validate_on_submit():
        Live = form.Live.data       #Get the Data.
        Login = form.Login.data
        Current_Group = form.Current_Group.data
        New_Group = form.New_Group.data
        sql_insert = "INSERT INTO  test.`changed_group_opencheck` (`Live`, `login`, `current_group`, `New_Group`, `Changed`, `Time_Changed`) VALUES" \
             " ({live},{login},'{current_group}','{new_group}',{changed},now() )".format(live=Live,login=Login, current_group=Current_Group,new_group=New_Group,changed=0)
        print(sql_insert)
        raw_insert_result = db.engine.execute(sql_insert)

    # elif request.method == 'POST' and form.validate_on_submit() == False:
    #     flash('Invalid Form Entry')


    return render_template("Change_USer_Group.html", form=form,title=title, header=header, description=Markup(description))


@app.route('/Risk_autocut_ajax', methods=['GET', 'POST'])
@login_required
def Risk_autocut_ajax():
    # TODO: Check if user exist first.

    live_to_run = [1, 3]  # Only want to run this on Live 1 and 3.

    # Raw SQL Statment. Will have to use .format(live=1) for example.
    raw_sql_statement = """SELECT mt4_users.LOGIN, X.LIVE, X.CURRENT_GROUP as `CURRENT_GROUP[CHECK]`, X.NEW_GROUP, mt4_users.`GROUP` as USER_CURRENT_GROUP,
    					CASE WHEN mt4_users.`GROUP` = X.CURRENT_GROUP THEN 'Yes' ELSE 'No' END as CURRENT_GROUP_TALLY, 
    					CASE WHEN X.NEW_GROUP IN (SELECT `GROUP` FROM Live{live}.mt4_groups WHERE `GROUP` LIKE X.NEW_GROUP) THEN 'Yes' ELSE 'No' END as NEW_GROUP_FOUND, 
    					COALESCE((SELECT count(*) FROM live{live}.mt4_trades WHERE mt4_trades.LOGIN = X.LOGIN AND CLOSE_TIME = "1970-01-01 00:00:00" GROUP BY mt4_trades.LOGIN),0) as OPEN_TRADE_COUNT
    			FROM Live{live}.mt4_users,(SELECT LIVE,LOGIN,CURRENT_GROUP,NEW_GROUP FROM test.changed_group_opencheck WHERE LIVE = '{live}' and `CHANGED` = 0 ) X
    			WHERE mt4_users.`ENABLE` = 1 and mt4_users.LOGIN = X.LOGIN """

    raw_sql_statement = raw_sql_statement.replace("\t", " ").replace("\n", " ")
    # construct the SQL Statment
    sql_query_statement = " UNION ".join([raw_sql_statement.format(live=l) for l in live_to_run])
    sql_result = Query_SQL_db_engine(sql_query_statement)  # Query SQL

    return_val = {}     #Initialise.

    C_Return = {}   # The returns from C++
    C_Return[0] = "User Changed"
    C_Return[-1] = "C++ ERROR: No Connection"
    C_Return[-2] = "C++ ERROR: New Group Not Found"
    C_Return[-3] = "C++ ERROR: User Current Group mismatched"
    C_Return[-4] = "C++ ERROR: Unknown Error"
    C_Return[-5] = "C++ ERROR: Open Trades"
    C_Return[-6] = "C++ ERROR: User Not Found!"
    C_Return[-10] = "C++ ERROR: Param Error"


    # Need to update Run time on SQL Update table.
    async_Update_Runtime("ChangeGroup_NoOpenTrades")

    if len(sql_result) == 0:    # If there are nothing to be changed.
        return_val = {"All": [{"Comment":"Login awaiting change: 0", "Last Query time": "{}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}]}
        return json.dumps(return_val)

    success_result = []
    success_listdict = []
    for i,d in enumerate(sql_result):
        comment =""
        error_flag = 0

        if not ("CURRENT_GROUP_TALLY" in d and d["CURRENT_GROUP_TALLY"].find("Yes") >=0):
            comment += "Current group doesn't match. "
            error_flag += 1
        if not ("NEW_GROUP_FOUND" in d and d["NEW_GROUP_FOUND"].find("Yes") >=0):
            comment += "New group not found. "
            error_flag += 1
        if ("OPEN_TRADE_COUNT" in d and d["OPEN_TRADE_COUNT"] == 0):
            if error_flag == 0: # No obvious error from the SQL Return Code.

                server = d["LIVE"] if "LIVE" in d else False
                login = d["LOGIN"] if "LOGIN" in d else False
                previous_group = d["USER_CURRENT_GROUP"] if "USER_CURRENT_GROUP" in d else False
                new_group = d["NEW_GROUP"] if "NEW_GROUP" in d else False
                if all([server,login,previous_group, new_group]):     # Need to run C++ Should there be anything to change.
                    # #(C_Return_Val, output, err)
                    #c_run_return= [0,0,0]   # Artificial Results.
                    c_run_return = Run_C_Prog("app" + url_for('static', filename='Exec/Change_User.exe') + " {server} {login} {previous_group} {new_group}".format(
                        server=server,login=login,previous_group=previous_group,new_group=new_group))


                    comment += C_Return[c_run_return[0]]
                    if c_run_return[0] == 0:    # If C++ Returns okay.
                        success_result.append((server, login, previous_group, new_group))
                        # Want to add into a list of dict. Want to change the _ of Keys to " " Spaces.
                        changed_user_buffer = dict(zip([k.replace("_", " ") for k in list(d.keys())], d.values()))
                        changed_user_buffer["UPDATED TIME"] = time_now()    # Want to add in the SGT that it was changed.
                        success_listdict.append(changed_user_buffer)
                else:
                    comment += "SQL Return Error. [LIVE, LOGIN, USER_CURRENT_GROUP, NEW_GROUP]"

        else:   # There are open trades. Cannot Change.
            comment += "Open trades found."
        sql_result[i]["Comment"] = comment if error_flag == 0 else "ERROR: {}".format(comment)

    if len(success_result) > 0:  # For those that are changed, We want to save it in SQL.
        # Want to get the WHERE statements for each.
        sql_where_statement = " OR ".join(["(LOGIN = {login} and LIVE = {server} and CURRENT_GROUP = '{previous_group}' and NEW_GROUP = '{new_group}') ".format(
            server=server, login=login,previous_group=previous_group,new_group=new_group) for (server, login, previous_group, new_group) in success_result])
        #print(sql_where_statement)

        # Construct the SQL Statement
        sql_update_statement = """UPDATE test.changed_group_opencheck set `CHANGED` = 1, TIME_CHANGED = now() where (	"""
        sql_update_statement += sql_where_statement
        sql_update_statement += """ ) and `CHANGED` = 0 and TIME_CHANGED = '1970-01-01 00:00:00'"""
        sql_update_statement = text(sql_update_statement)   # To SQL Friendly Text.
        raw_insert_result = db.engine.execute(sql_update_statement) # TO SQL


    val = [list(a.values()) for a in sql_result]
    key = list(sql_result[0].keys())
    key = [k.replace("_"," ") for k in key]     # Want to space things out instead of _
    return_val = {"All": [dict(zip(key,v)) for v in val], "Changed": success_listdict}




    #table = create_table_fun(sql_result)
    return json.dumps(return_val)





@app.route('/g', methods=['GET', 'POST'])
def read_from_app_g():


    # print(app.config["MAIL_SERVER"])
    # print(app.config["MAIL_PORT"])
    # print(app.config["MAIL_USE_TLS"])
    # print(app.config["MAIL_USERNAME"])
    # print(app.config["MAIL_PASSWORD"])

    # if "Swap_data" in g:
    #     print("Swap_data in g")
    # else:
    #     print("Swap_data Data? ")
    return render_template("upload_form.html")



@app.route('/h', methods=['GET', 'POST'])
def read_from_app_h():

    # Time = datetime.now().strftime("%H:%M:%S")
    # for t in range(10):
    #     SymbolTotalTest.append_field(str(t) + " " + str(Time), FormField(SymbolSwap))
    # form = SymbolTotalTest()
    #return render_template("standard_form.html", form=form)
    return render_template("Standard_Single_Table.html", backgroud_Filename='css/test7.jpg', Table_name="Table1", title="Table", ajax_url=url_for("LP_Margin_UpdateTime"))

# To check if the file exists. If it does, generate a new name.
def Check_File_Exist(path, filename):
    folders = [a for a in path.split("/") if (a != "" and a != ".")]
    for i, folder in enumerate(folders):
        folder = "/".join(folders[:i + 1])  # WE Want the current one as well.
        if os.path.isdir(folder) == False:
            os.mkdir(folder)
    File_Counter = 0
    FileName = filename  # To be used and changed later. Appended to the end.
    while True:
        full_path_filename = path + "/" + FileName
        if os.path.isfile(full_path_filename) == False:
            break
        else:
            File_Counter += 1
            FileName_Split = filename.split(".")
            FileName_Split[-2] = FileName_Split[-2] + "_" + str(File_Counter)
            FileName = ".".join(FileName_Split)

    return path + "/" + FileName


def markup_swaps(Val, positive_markup, negative_markup ):
    val = Val
    if val >= 0:  # Positive!
        markup_percentage = float(positive_markup)
        val = val * (100 - markup_percentage) / 100
    else:
        markup_percentage = float(negative_markup)
        val = val * (100 + markup_percentage) / 100
    return val


def Check_Float(element):
    try:
        float(element)
        return True
    except ValueError:
        print ("Not a float")
        return False

# Need to have a generic page that does all the SQL Query RAW



@app.route('/is_prime')
@login_required
def is_prime_query_AccDetails():    #Query Is Prime

    #is_prime_query_AccDetails_json()
    return render_template("Is_prime_html.html",header="IS Prime Account Details")


@app.route('/is_prime_return_json', methods=['GET', 'POST'])    #Query Is Prime, Returns a Json.
@login_required
def is_prime_query_AccDetails_json():
    API_URL_BASE = 'https://api.isprimefx.com/api/'
    USERNAME = "aaron.lim@blackwellglobal.com"
    PASSWORD = "resortshoppingstaff"

    # login and extract the authentication token
    response = requests.post(API_URL_BASE + 'login', \
    headers={'Content-Type': 'application/json'}, data=json.dumps({'username': USERNAME, 'password': PASSWORD}), verify=False)
    token = response.json()['token']
    headers = {'X-Token': token}

    response = requests.get(API_URL_BASE + '/risk/positions', headers=headers, verify=False)
    dict_response = json.loads(json.dumps((response.json())))

    account_dict = {}

    for s in dict_response:
        if "groupName" in s and s["groupName"] ==  "Blackwell Global BVI Risk 2":   # Making sure its the right account.
            account_dict = s
            lp = "Is Prime Terminus"
            account_balance = s["collateral"]
            account_margin_use = s["requirement"]
            account_floating = s["unrealisedPnl"]
            account_equity = s["netEquity"]
            account_free_margin = s["preDeliveredCollateral"]
            account_credit = 0
            account_margin_call = 100
            account_stop_out = 0
            account_stop_out_amount = 0

            sql_insert = "INSERT INTO  aaron.`bgi_hedge_lp_summary` \
            (`lp`, `deposit`, `pnl`, `equity`, `total_margin`, `free_margin`, `credit`, `margin_call(E/M)`, `stop_out(E/M)`, `stop_out_amount`, `updated_time(SGT)`) VALUES" \
                         " ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',NOW()) ".format(lp, account_balance, account_floating, account_equity, account_margin_use, account_free_margin, \
                                                                                                  account_credit, account_margin_call,account_stop_out, account_stop_out_amount)
            SQL_LP_Footer = " ON DUPLICATE KEY UPDATE deposit = VALUES(deposit), pnl = VALUES(pnl), equity = VALUES(equity), total_margin = VALUES(total_margin), free_margin = VALUES(free_margin), `updated_time(SGT)` = VALUES(`updated_time(SGT)`), credit = VALUES(credit), `margin_call(E/M)` = VALUES(`margin_call(E/M)`),`stop_out(E/M)` = VALUES(`stop_out(E/M)`) ";

            sql_insert += SQL_LP_Footer

            #print(sql_insert)
            raw_insert_result = db.engine.execute(sql_insert)
            raw_insert_result

    for s in account_dict:
        if isinstance(account_dict[s], float) or isinstance(account_dict[s], int):
            account_dict[s] = "{:,.2f}".format(account_dict[s])

    account_dict["Updated_Time(SGT)"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    table = create_table_fun([account_dict])

    return json.dumps(account_dict)


@app.route('/MT5_Modify_Trade', methods=['GET', 'POST'])
@login_required
def Modify_MT5_Trades():    # To upload the Files, or post which trades to delete on MT5
    form = MT5_Modify_Trades_Form()
    # file_form = File_Form()

    if request.method == 'POST':
        print("POST Method")
        if form.validate_on_submit():
            MT5_Login = form.MT5_Login.data  # Get the Data.
            MT5_Deal_Num = form.MT5_Deal_Num.data
            MT5_Comment = form.MT5_Comment.data
            MT5_Action = form.MT5_Action.data
            print("Login: {login}, Deal: {deal}, Action: {action}, New Comment: {new_comment}".format(login=MT5_Login, deal=MT5_Deal_Num, action=MT5_Action, new_comment=MT5_Comment))
        else:
            print("Not Validated. ")

        #
        # if file_form.validate_on_submit():
        #     record_dict = request.get_records(field_name='upload', name_columns_by_row=0)
        #     print(record_dict)
            #df_uploaded_data = pd.DataFrame(record_dict)
            #print(df_uploaded_data)
    return render_template("MT5_Modify_Trades.html", form=form, header="MT5 Modify Trades", description="MT5 Modify Trades")



@app.route('/Get_Live3_MT4User')
@login_required
def Live3_MT4_Users():    # To upload the Files, or post which trades to delete on MT5
    raw_result = db.engine.execute('select login, `GROUP`, `NAME`, CURRENCY, REGDATE from live3.mt4_users ')
    #raw_result = db.engine.execute("select login, `NAME`, REGDATE, `GROUP`, CURRENCY from live3.mt4_users where login = 102")
    result_data = raw_result.fetchall()
    result_col = raw_result.keys()
    df_users = pd.DataFrame(data=result_data, columns=result_col)
    df_users["REGDATE"] = df_users["REGDATE"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S"))
    return excel.make_response_from_array(list([result_col]) + list(df_users.values), 'csv', file_name="Live3_Users.csv")


@app.route('/sent_file/Risk_Download')
@login_required
def Live3_MT4_Users_web():    # To upload the Files, or post which trades to delete on MT5
    return render_template("Show_Table.html",header="Send file...",title="Risk Download Page")


@app.route('/ABook_Match_Trades')
@login_required
def ABook_Matching():    # To upload the Files, or post which trades to delete on MT5

    return render_template("A_Book_Matching.html",header="A Book Matching", title="LP/MT4 Position")


@app.route('/ABook_Match_Trades_Position', methods=['GET', 'POST'])
@login_required
def ABook_Matching_Position_Vol():    # To upload the Files, or post which trades to delete on MT5

    mismatch_count_1 = 10   # Notify when mismatch has lasted 1st time.
    mismatch_count_2 = 15   # Second notify when mismatched has lasted a second time

    sql_query = text("""SELECT SYMBOL,COALESCE(vantage_LOT,0) AS Vantage_lot,COALESCE(squared_LOT,0) AS Squared_lot,COALESCE(api_LOT,0) AS API_lot,COALESCE(offset_LOT,0) AS Offset_lot,COALESCE(vantage_LOT,0)+COALESCE(squared_LOT,0)-COALESCE(api_LOT,0)+COALESCE(offset_LOT,0) AS Lp_Net_Vol
		,COALESCE(S.mt4_NET_VOL,0) AS MT4_Net_Vol ,COALESCE(vantage_LOT,0)+COALESCE(squared_LOT,0)-COALESCE(api_LOT,0)+COALESCE(offset_LOT,0)-COALESCE(S.mt4_NET_VOL,0) AS Discrepancy FROM test.core_symbol
		LEFT JOIN
		(SELECT mt4_symbol AS vantage_SYMBOL,ROUND(SUM(vantage_LOT),2) AS vantage_LOT FROM (SELECT coresymbol,position/core_symbol.CONTRACT_SIZE AS vantage_LOT,mt4_symbol FROM test.`vantage_live_trades` 
		LEFT JOIN test.vantage_margin_symbol ON vantage_live_trades.coresymbol = vantage_margin_symbol.margin_symbol LEFT JOIN test.core_symbol ON vantage_margin_symbol.mt4_symbol = core_symbol.SYMBOL WHERE CONTRACT_SIZE>0) AS B GROUP BY mt4_symbol) AS Y ON core_symbol.SYMBOL = Y.vantage_SYMBOL
		LEFT JOIN
		(SELECT Symbol AS squared_SYMBOL,ROUND(SUM(LOT),2) AS squared_LOT FROM (SELECT COALESCE(live_trade_squaredpromt4_live_covertsymbol.SYMBOL,live_trade_5830001_squaredpromt4_live.Symbol) AS Symbol,CASE WHEN Cmd = 0 THEN lots WHEN Cmd = 1 THEN lots * (-1) END AS LOT,Cmd FROM test.`live_trade_5830001_squaredpromt4_live` 
		LEFT JOIN test.live_trade_squaredpromt4_live_covertsymbol ON live_trade_5830001_squaredpromt4_live.Symbol = live_trade_squaredpromt4_live_covertsymbol.SQUARED_SYMBOL WHERE close_time = '1970-01-01 00:00:00') AS A GROUP BY Symbol) AS Z ON core_symbol.SYMBOL = Z.squared_SYMBOL
		LEFT JOIN
		(SELECT coresymbol AS api_SYMBOL,ROUND(SUM(api_LOT),2) AS api_LOT FROM (SELECT bgimargin_live_trades.margin_id,bgimargin_live_trades.coresymbol,position/core_symbol.CONTRACT_SIZE AS api_LOT FROM test.`bgimargin_live_trades` 
		LEFT JOIN test.core_symbol ON bgimargin_live_trades.coresymbol = core_symbol.SYMBOL WHERE CONTRACT_SIZE>0) AS B GROUP BY coresymbol) AS K ON core_symbol.SYMBOL = K.api_SYMBOL
		LEFT JOIN
		(SELECT SYMBOL AS offset_SYMBOL,ROUND(SUM(LOTS),2) AS offset_LOT FROM test.offset_live_trades GROUP BY SYMBOL) AS P ON core_symbol.SYMBOL = P.offset_SYMBOL
		LEFT JOIN
		(SELECT SYMBOL AS mt4_SYMBOL,ROUND(SUM(VOL),2) AS mt4_NET_VOL FROM
		(SELECT 'live1' AS LIVE,SUM(CASE WHEN (mt4_trades.CMD = 0) THEN mt4_trades.VOLUME*0.01 WHEN (mt4_trades.CMD = 1) THEN mt4_trades.VOLUME*(-1)*0.01 ELSE 0 END) AS VOL, 
		(CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END) AS `SYMBOL` 
		FROM live1.mt4_trades WHERE ((mt4_trades.`GROUP` IN (SELECT `GROUP` FROM live1.a_group)) OR (LOGIN IN (SELECT LOGIN FROM live1.a_login )))
		AND LENGTH(mt4_trades.SYMBOL)>0 AND mt4_trades.CLOSE_TIME = '1970-01-01 00:00:00' AND CMD < 2
		GROUP BY (CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END)
		UNION
		SELECT 'live2' AS LIVE,SUM(CASE WHEN (mt4_trades.CMD = 0) THEN mt4_trades.VOLUME*0.01 WHEN (mt4_trades.CMD = 1) THEN mt4_trades.VOLUME*(-1)*0.01 ELSE 0 END) AS VOL, 
		(CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END) AS `SYMBOL` 
		FROM live2.mt4_trades WHERE ((mt4_trades.`GROUP` IN (SELECT `GROUP` FROM live2.a_group)) OR (LOGIN IN (SELECT LOGIN FROM live2.a_login )) OR LOGIN = '9583' OR LOGIN = '9615' OR LOGIN = '9618' OR (mt4_trades.`GROUP` LIKE 'A_ATG%' AND VOLUME > 1501))
		AND LENGTH(mt4_trades.SYMBOL)>0 AND mt4_trades.CLOSE_TIME = '1970-01-01 00:00:00' AND CMD < 2 GROUP BY (CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END)
		UNION
		SELECT 'live3' AS LIVE,SUM(CASE WHEN (mt4_trades.CMD = 0) THEN mt4_trades.VOLUME*0.01 WHEN (mt4_trades.CMD = 1) THEN mt4_trades.VOLUME*(-1)*0.01 ELSE 0 END) AS VOL, 
		(CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END) AS `SYMBOL` 
		FROM live3.mt4_trades WHERE (mt4_trades.`GROUP` IN (SELECT `GROUP` FROM live3.a_group)) 
		AND LENGTH(mt4_trades.SYMBOL)>0 AND mt4_trades.CLOSE_TIME = '1970-01-01 00:00:00' AND CMD < 2 GROUP BY (CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END)
		UNION
		SELECT 'live5' AS LIVE,SUM(CASE WHEN (mt4_trades.CMD = 0) THEN mt4_trades.VOLUME*0.01 WHEN (mt4_trades.CMD = 1) THEN mt4_trades.VOLUME*(-1)*0.01 ELSE 0 END) AS VOL, 
		(CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END) AS `SYMBOL` 
		FROM live5.mt4_trades WHERE (mt4_trades.`GROUP` IN (SELECT `GROUP` FROM live5.a_group))
		AND LENGTH(mt4_trades.SYMBOL)>0 AND mt4_trades.CLOSE_TIME = '1970-01-01 00:00:00' AND CMD < 2 GROUP BY (CASE WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%y' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'y',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%q' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'q',1) 
		WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%`' THEN SUBSTRING_INDEX(SUBSTRING_INDEX(SYMBOL,'.',2),'`',1) WHEN SUBSTRING_INDEX(SYMBOL,'.',2) LIKE '.%' THEN SUBSTRING_INDEX(SYMBOL,'.',2) ELSE LEFT(SYMBOL,6) END)
		) AS X GROUP BY SYMBOL) S ON core_symbol.SYMBOL = S.mt4_SYMBOL ORDER BY ABS(Discrepancy) DESC, ABS(MT4_Net_Vol) DESC, SYMBOL""")


    curent_result = Query_SQL_db_engine(sql_query)  # Function to do the Query and return zip dict.


    #curent_result[10]["Discrepancy"] = 0.1  # Artificially induce a mismatch

    if request.method == 'POST':    # If the request came in thru a POST. We will get the data first.

        post_data = dict(request.form)
        #print(post_data)
        # Check if we need to send Email
        Send_Email_Flag =  int(post_data["send_email_flag"][0]) if ("send_email_flag" in post_data) \
                                                                   and (isinstance(post_data['send_email_flag'], list)) else 0
        # Check for the past details.
        Past_Details = json.loads(post_data["MT4_LP_Position_save"][0]) if ("MT4_LP_Position_save" in post_data) \
                                                                           and (isinstance(post_data['MT4_LP_Position_save'], list)) \
                                                                           and is_json(post_data["MT4_LP_Position_save"][0]) \
                                                                            else None
        Send_Email_Total = int(post_data["Send_Email_Total"][0]) if ("Send_Email_Total" in post_data) \
                                                                   and (isinstance(post_data['Send_Email_Total'], list)) else 0



        # Variables to return.
        Play_Sound = 0                                  # To play sound if needed

        #print(Past_Details)
        # To Calculate the past (Previous result) Mismatches
        Past_discrepancy = {}
        for pd in Past_Details:
            if "SYMBOL" in pd and "Discrepancy" in pd.keys() and pd["Discrepancy"] != 0:    #If the keys are there.
                    Past_discrepancy[pd["SYMBOL"]] = pd["Mismatch_count"] if "Mismatch_count" in pd else 1  # Want to get the count. Or raise as 1.

        #curent_result[0]["Discrepancy"] = 0.01

        # To tally off with current mismatches. If there are, add 1 to count. Else, Zero it.
        for d in curent_result:
            if "Discrepancy" in d.keys():
                if d["Discrepancy"] != 0:   # There are mismatches Currently.
                    d["Mismatch_count"] = 1 if d['SYMBOL'] not in Past_discrepancy else Past_discrepancy[d['SYMBOL']] + 1
                else:
                    d["Mismatch_count"] = 0

        # Want to get all the mismatches.
        Notify_Mismatch = [d for d in curent_result if d['Mismatch_count'] != 0 ]

        Current_discrepancy = [d["SYMBOL"] for d in Notify_Mismatch]        # Get all the Mimatch Symbols only

        if (Send_Email_Total == 1): # for sending the total position.

            email_table_html = Array_To_HTML_Table(list(curent_result[0].keys()),
                                                            [list(d.values()) for d in curent_result])

            email_title = "ABook Position(Total, with {} mismatches.)".format(len(Notify_Mismatch)) \
            if len(Notify_Mismatch) > 0 else "ABook Position(Total)"

            async_send_email(EMAIL_LIST_ALERT, [],
                             email_title,
                             Email_Header + "Hi, <br><br>Kindly find the total position of the MT4/LP Position. <br> "
                             + email_table_html + "<br>Thanks,<br>Aaron" + Email_Footer, [])
        else:
            if Send_Email_Flag == 1:  # Only when Send Email Alert is set, we will

                # Want to update the runtime table to ensure that tool is running.
                sql_insert = "INSERT INTO  aaron.`monitor_tool_runtime` (`Monitor_Tool`, `Updated_Time`) VALUES" + \
                             " ('MT4/LP A Book Check', now()) ON DUPLICATE KEY UPDATE Updated_Time=now()"
                #print(sql_insert)
                raw_insert_result = db.engine.execute(sql_insert)

            Tele_Message = "*MT4/LP Position* \n"  # To compose Telegram outgoing message
            email_html_body = "Hi, <br><br>";
            Email_Title_Array = []

            # If there are mismatch count that are either mismatch_count_1 or mismatch_count_2, we will send the email.
            if any([(d["Mismatch_count"] == mismatch_count_1) or (d["Mismatch_count"] == mismatch_count_2) for d in Notify_Mismatch]):    # If there are to be notified.
                Play_Sound += 1  # Raise the flag to play sound.
                Notify_mismatch_table_html = Array_To_HTML_Table(list(Notify_Mismatch[0].keys()), [list(d.values()) for d in Notify_Mismatch])
                Email_Title_Array.append("Mismatch")
                email_html_body +=  "There is a mismatch for A-Book LP/MT4 trades.<br>{}".format(Notify_mismatch_table_html)
                #print(Notify_Mismatch)
                Tele_Message += "{} mismatch: {}\n".format(len(Current_discrepancy), ", ".join(["{} ({})".format(c["SYMBOL"], c["Discrepancy"]) for c in Notify_Mismatch]))

            Cleared_Symbol = [sym for sym,count in Past_discrepancy.items() if (sym not in Current_discrepancy) and (count >= mismatch_count_1) ]    # Symbol that had mismatches and now it's been cleared.

            # If Mismatchs have been cleared.
            if len(Cleared_Symbol) > 0:     # There are symbols that have been cleared
                # Get the Symbol data from current SQL return data.
                Cleared_Symbol_data = [d for d in curent_result if "SYMBOL" in d and d["SYMBOL"] in Cleared_Symbol]
                # Create the HTML Table
                Notify_cleared_table_html = Array_To_HTML_Table(list(Cleared_Symbol_data[0].keys()),
                                                                 [list(d.values()) for d in Cleared_Symbol_data])
                Email_Title_Array.append("Cleared")
                email_html_body += "The Following symbol/s mismatch have been cleared: {} <br> {}".format(", ".join(Cleared_Symbol), Notify_cleared_table_html)
                Tele_Message += "{} Cleared: {}\n".format(len(Cleared_Symbol), ", ".join(Cleared_Symbol))




            if Send_Email_Flag == 1 and len(Email_Title_Array) > 0:    # If there are things to be sent, we determine by looking at the title array
                api_update_details = json.loads(LP_Margin_UpdateTime())  # Want to get the API/LP Update time.

                email_html_body +=  "The API/LP Update timings:<br>" + Array_To_HTML_Table(
                    list(api_update_details[0].keys()), [list(api_update_details[0].values())], ["Update Slow"])
                email_html_body += "This Email was generated at: SGT {}.<br><br>Thanks,<br>Aaron".format(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                # Send the email
                async_send_email(EMAIL_LIST_ALERT, [], "A Book Position ({}) ".format("/ ".join(Email_Title_Array)),
                       Email_Header + email_html_body + Email_Footer, [])

                #Send the Telegram message.
                async_Post_To_Telegram(TELE_ID_MTLP_MISMATCH, Tele_Message, TELE_CLIENT_ID)





        #'[{"Vantage_Update_Time": "2019-09-17 16:54:20", "BGI_Margin_Update_Time": "2019-09-17 16:54:23"}]'


    return_result = {"current_result":curent_result, "Play_Sound": Play_Sound}   # End of if/else. going to return.

    return json.dumps(return_result)


@app.route('/ABook_LP_Details', methods=['GET', 'POST'])
@login_required
def ABook_LP_Details():    # LP Details. Balance, Credit, Margin, MC/SO levels. Will alert if email is set to send.
                            # Checks Margin against MC/SO values, with some buffer as alert.

    sql_query = text("""SELECT lp, deposit, credit, pnl, equity, total_margin, free_margin, 
		ROUND((credit + deposit + pnl),2) as EQUITY, 
		ROUND(100 * total_margin / (credit + deposit + pnl),2) as `Margin/Equity (%)` ,
		margin_call as `margin_call (M/E)` , stop_out as `stop_out (M/E)`,
			  COALESCE(`stop_out_amount`, ROUND(  100* (`total_margin`/`stop_out`) ,2)) as `STOPOUT AMOUNT`,
		ROUND(`equity` -  COALESCE(`stop_out_amount`,         100* (`total_margin`/`stop_out`) ),2) as `available`,
		updated_time 
		FROM aaron.lp_summary""")  # Need to convert to Python Friendly Text.
    raw_result = db.engine.execute(sql_query)
    result_data = raw_result.fetchall()
    #result_data_json_parse = [[float(a) if isinstance(a, decimal.Decimal) else a for a in d ] for d in result_data]    # correct The decimal.Decimal class to float.
    result_data_json_parse = [[Time_difference_Check(a) if isinstance(a, datetime.datetime) else a for a in d] for d in
                           result_data]  # correct The decimal.Decimal class to float.

    result_col = raw_result.keys()
    return_result = [dict(zip(result_col,d)) for d in result_data_json_parse]


    LP_Position_Show_Table = [] # to store the LP details in a more read-able sense

    Tele_Margin_Text = "*LP Margin Issues.*\n"    # To Compose Telegram text for Margin issues.
    Margin_Attention_Flag = 0
    Margin_MC_Flag = 0
    Margin_SO_Flag = 0
    Play_Sound = 0  # For return to AJAX


    for i,lp in enumerate(return_result):    # Want to re-arrange.
        loop_buffer = {}
        loop_buffer["LP"] = lp["lp"] if "lp" in lp else None

        Lp_MC_Level = lp["margin_call (M/E)"] if "margin_call (M/E)" in lp else None
        Lp_SO_Level = lp["stop_out (M/E)"] if "stop_out (M/E)" in lp else None
        Lp_Margin_Level = lp["Margin/Equity (%)"]  if "Margin/Equity (%)" in lp else None

        loop_buffer["BALANCE"] = {}
        loop_buffer["BALANCE"]["DEPOSIT"] = "$ {:,.2f}".format(float(lp["deposit"])) if "deposit" in lp else None
        loop_buffer["BALANCE"]["CREDIT"] = "$ {:,.2f}".format(float(lp["credit"])) if "credit" in lp else None
        loop_buffer["BALANCE"]["PNL"] = "$ {:,.2f}".format(float(lp["pnl"])) if "pnl" in lp else None
        loop_buffer["BALANCE"]["EQUITY"] = "$ {:,.2f}".format(float(lp["equity"])) if "equity" in lp else None

        loop_buffer["MARGIN"] = {}
        loop_buffer["MARGIN"]["TOTAL_MARGIN"] = "${:,.2f}".format(float(lp["total_margin"])) if "total_margin" in lp else None
        loop_buffer["MARGIN"]["FREE_MARGIN"] = "${:,.2f}".format(float(lp["free_margin"])) if "free_margin" in lp else None

        # Checking Margin Levels.
        if Lp_Margin_Level >= (Lp_SO_Level - LP_MARGIN_ALERT_LEVEL):    # Check SO Level First.
            Margin_SO_Flag +=1
            loop_buffer["MARGIN/EQUITY (%)"] = "SO Alert: {:.2f}%".format(Lp_Margin_Level)
            Tele_Margin_Text += "_SO Alert_: {} margin is at {:.2f}.\n".format( loop_buffer["LP"], Lp_Margin_Level)
        elif Lp_Margin_Level >= Lp_MC_Level:                            # Check Margin Call Level
            Margin_MC_Flag += 1
            loop_buffer["MARGIN/EQUITY (%)"] = "Margin Call: {:.2f}%".format(Lp_Margin_Level)
            Tele_Margin_Text += "_MC Alert_: {} margin is at {}. MC/SO: {:.2f}/{:.2f}\n".format(loop_buffer["LP"], Lp_Margin_Level,Lp_MC_Level,Lp_SO_Level)
        elif Lp_Margin_Level >= (Lp_MC_Level - LP_MARGIN_ALERT_LEVEL):  # Want to start an alert when reaching MC.
            Margin_Attention_Flag += 1
            loop_buffer["MARGIN/EQUITY (%)"] = "Alert: {:.2f}%".format(Lp_Margin_Level)
            Tele_Margin_Text += "_Margin Alert_: {} margin is at {}. MC is at {:.2f}\n".format(loop_buffer["LP"], Lp_Margin_Level, Lp_MC_Level)
        else:
            loop_buffer["MARGIN/EQUITY (%)"] = "{}%".format(Lp_Margin_Level)

        loop_buffer["MC/SO/AVALIABLE"] = {}
        loop_buffer["MC/SO/AVALIABLE"]["MARGIN_CALL (M/E)"] = "{:.2f}".format(Lp_MC_Level)
        loop_buffer["MC/SO/AVALIABLE"]["STOP_OUT (M/E)"] = "{:.2f}".format(Lp_SO_Level)
        loop_buffer["MC/SO/AVALIABLE"]["STOPOUT AMOUNT"] = "$ {:,.2f}".format(float(lp["STOPOUT AMOUNT"])) if "STOPOUT AMOUNT" in lp else None
        loop_buffer["MC/SO/AVALIABLE"]["AVALIABLE"] = "$ {:,.2f}".format(float(lp["available"])) if "available" in lp else None

        loop_buffer["UPDATED_TIME"] = lp["updated_time"] if "updated_time" in lp else None

        LP_Position_Show_Table.append(loop_buffer)
        #print(loop_buffer)

    if request.method == 'POST':
        post_data = dict(request.form)
        #print(post_data)

        # Get variables from POST.
        Send_Email_Flag = int(post_data["send_email_flag"][0]) if ("send_email_flag" in post_data) \
                               and (isinstance(post_data['send_email_flag'], list)) else 0
        lp_attention_email_count = int(post_data["lp_attention_email_count"][0]) if ("lp_attention_email_count" in post_data) \
                                and (isinstance(post_data['lp_attention_email_count'], list)) else 0

        lp_mc_email_count = int(post_data["lp_mc_email_count"][0]) if ("lp_mc_email_count" in post_data) \
                                 and (isinstance(post_data['lp_mc_email_count'], list)) else 0
        lp_time_issue_count = int(post_data["lp_time_issue_count"][0]) if ("lp_time_issue_count" in post_data) \
                                 and (isinstance(post_data['lp_time_issue_count'], list)) else -1
        lp_so_email_count = int(post_data["lp_so_email_count"][0]) if ("lp_so_email_count" in post_data) \
                                and (isinstance(post_data['lp_so_email_count'], list)) else -1


        if Send_Email_Flag == 1:    # Want to update the runtime table to ensure that tool is running.

            sql_insert = "INSERT INTO  aaron.`monitor_tool_runtime` (`Monitor_Tool`, `Updated_Time`) VALUES" \
                         " ('LP Details Check', now()) ON DUPLICATE KEY UPDATE Updated_Time=now()"
            raw_insert_result = db.engine.execute(sql_insert)

        Tele_Message = "*LP Details* \n"  # To compose Telegram outgoing message

        # Checking if there are any update time that are slow. Returns a Bool
        update_time_slow = any([[True for a in d if (isinstance(a, datetime.datetime) and abs((a-datetime.datetime.now()).total_seconds()) > TIME_UPDATE_SLOW_MIN*60)] for d in result_data])


        if update_time_slow: # Want to send an email out if time is slow.
            if lp_time_issue_count == 0:    # For time issue.
                if Send_Email_Flag == 1:
                    LP_position_Table = List_of_Dict_To_Horizontal_HTML_Table(LP_Position_Show_Table, ['Slow', 'Margin Call', 'Alert'])

                    async_send_email(To_recipients=EMAIL_LIST_ALERT, cc_recipients=[],
                                     Subject="LP Details not updating",
                                     HTML_Text="{}Hi,<br><br>LP Details not updating. <br>{}<br>This Email was generated at: {} (SGT)<br><br>Thanks,<br>Aaron{}".format(
                                         Email_Header, LP_position_Table, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") ,Email_Footer), Attachment_Name=[])


                    LP_Issue_Name = [d['lp'] for d in result_data if ("lp" in d) and ("updated_time" in d) and abs(
                        (d["updated_time"] - datetime.datetime.now()).total_seconds()) > (TIME_UPDATE_SLOW_MIN * 60)]
                    Tele_Message += "_Update Slow_: {}\n".format(", ".join(LP_Issue_Name))

                    async_Post_To_Telegram(TELE_ID_MTLP_MISMATCH, Tele_Message, TELE_CLIENT_ID)

                Play_Sound+=1   # No matter sending emails or not, we will need to play sound.
                lp_time_issue_count += 1
        else:   # Reset to 0.
            lp_time_issue_count = 0


        #-------------------- To Check the Margin Levels, and to send email when needed. --------------------------
        if Margin_SO_Flag > 0:   # If there are margin issues. Want to send Alert Out.
            if lp_so_email_count == 0:
                if Send_Email_Flag == 1:
                    async_Post_To_Telegram(TELE_ID_MTLP_MISMATCH, Tele_Margin_Text, TELE_CLIENT_ID)
                    LP_position_Table = List_of_Dict_To_Horizontal_HTML_Table(LP_Position_Show_Table, ['Slow', 'Margin Call', 'Alert'])
                    async_send_email(To_recipients=EMAIL_LIST_ALERT, cc_recipients=[],
                                     Subject = "LP Account Approaching SO.",
                                     HTML_Text="{}Hi,<br><br>LP Account margin reaching SO Levels. <br>{}<br>This Email was generated at: {} (SGT)<br><br>Thanks,<br>Aaron{}".
                                     format(Email_Header, LP_position_Table, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),Email_Footer),
                                     Attachment_Name=[])
            Play_Sound += 1  # No matter sending emails or not, we will need to play sound.
            #print("Play Sound: {}".format(Play_Sound))
            lp_so_email_count += 1
            lp_mc_email_count = lp_mc_email_count + 1 if lp_mc_email_count <1 else lp_mc_email_count    # Want to raise all to at least 1
            Margin_Attention_Flag = Margin_Attention_Flag + 1 if Margin_Attention_Flag < 1 else Margin_Attention_Flag
        elif Margin_MC_Flag > 0:   # If there are margin issues. Want to send Alert Out.
            if lp_mc_email_count == 0:
                if Send_Email_Flag == 1:
                    LP_position_Table = List_of_Dict_To_Horizontal_HTML_Table(LP_Position_Show_Table, ['Slow', 'Margin Call', 'Alert'])
                    async_send_email(To_recipients=EMAIL_LIST_ALERT, cc_recipients=[],
                                     Subject = "LP Account has passed MC Levels.",
                                     HTML_Text="{}Hi,<br><br>LP Account margin reaching SO Levels. <br>{}<br>This Email was generated at: {} (SGT)<br><br>Thanks,<br>Aaron{}".
                                     format(Email_Header, LP_position_Table, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),Email_Footer),
                                     Attachment_Name=[])
                    async_Post_To_Telegram(TELE_ID_MTLP_MISMATCH, Tele_Margin_Text, TELE_CLIENT_ID)
                Play_Sound += 1             # Play sound when MC. Once
            lp_mc_email_count += 1
            lp_so_email_count = 0
        elif Margin_Attention_Flag > 0:  # If there are margin issues. Want to send Alert Out
            if lp_attention_email_count == 0:
                if Send_Email_Flag == 1:
                    async_Post_To_Telegram(TELE_ID_MTLP_MISMATCH, Tele_Margin_Text, TELE_CLIENT_ID)
                    LP_position_Table = List_of_Dict_To_Horizontal_HTML_Table(LP_Position_Show_Table, ['Slow', 'Margin Call', 'Alert'])
                    async_send_email(To_recipients=EMAIL_LIST_ALERT, cc_recipients=[],
                                     Subject = "LP Account Approaching MC.",
                                     HTML_Text="{}Hi,<br><br>LP Account margin reaching SO Levels. <br>{}<br>This Email was generated at: {} (SGT)<br><br>Thanks,<br>Aaron{}".
                                     format(Email_Header, LP_position_Table, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),Email_Footer),
                                     Attachment_Name=[])
                Play_Sound += 1              # Play sound when Nearing MC. Once
            lp_attention_email_count += 1
            lp_so_email_count = 0
            lp_mc_email_count = 0

        else:       # Clear all flags.
            lp_so_email_count = 0
            lp_mc_email_count = 0
            lp_attention_email_count = 0
       # , "Alert", "Margin Call", "SO Attention"

            #return "Error:lalalala"
    return json.dumps({"lp_attention_email_count": lp_attention_email_count, "Play_Sound": Play_Sound, "current_result": LP_Position_Show_Table, "lp_time_issue_count": lp_time_issue_count,
                       "lp_so_email_count": lp_so_email_count, "lp_mc_email_count": lp_mc_email_count})



@app.route('/LP_Margin_UpdateTime', methods=['GET', 'POST'])
@login_required
def LP_Margin_UpdateTime():     # To query for LP/Margin Update time to check that it's being updated.
    #TODO: To add in sutible alert should this stop updating and such.
    # TODO: Date return as String instead of datetime. Cannot compare the date to notify when it's slow.
    sql_query = text("""select
    COALESCE(Vantage_Update_Time, 'No Open Trades') as Vantage_Update_Time,
    COALESCE(BGI_Margin_Updated_Time, 'No Open Trades') as BGI_Margin_Update_Time
    from
    (select min(updated_time) as Vantage_Update_Time from test.vantage_live_trades where position != 0) as V,
    (select updated_time as BGI_Margin_Updated_Time from test.bgimargin_live_trades where coresymbol = 'update') as BGI""")

    raw_result = db.engine.execute(sql_query)
    result_data = raw_result.fetchall()

    result_data_json_parse = [[try_string_to_datetime(a)  for a in d] for d in result_data]
    #result_data_json_parse = [[float(a) if isinstance(a, decimal.Decimal) else a for a in d ] for d in result_data]    # correct The decimal.Decimal class to float.
    result_data_json_parse = [[Time_difference_Check(a) if isinstance(a, datetime.datetime) else a for a in d] for d in
                              result_data_json_parse]  # correct The decimal.Decimal class to float.

    result_col = raw_result.keys()
    # Want to do a time check.
    result_data_json_parse = [Time_difference_Check(d) if isinstance(d, datetime.datetime) else d for d in result_data_json_parse]
    return_result = [dict(zip(result_col,d)) for d in result_data_json_parse]

    return json.dumps(return_result)

# Test if the string will return as date. if not, return string.
def try_string_to_datetime(sstr):
    try:
        d = datetime.datetime.strptime(sstr, '%Y-%m-%d %H:%M:%S')
        return d
    except:
        return sstr

@app.route('/Bloomberg_Dividend')
@login_required
def Bloomberg_Dividend():
    description = Markup("Dividend Values in the table above are 1-day early, when the values are uploaded as swaps onto MT4. <br>\
    Dividend would be given out/charged the next working day.")
    return render_template("Standard_Single_Table.html", backgroud_Filename='css/Charts.jpg', Table_name="CFD Dividend", \
                           title="CFD Dividend", ajax_url=url_for("Bloomberg_Dividend_ajax"),
                           description=description, replace_words=Markup(["Today"]))



@app.route('/Bloomberg_Dividend_ajax', methods=['GET', 'POST'])
@login_required
def Bloomberg_Dividend_ajax():     # Return the Bloomberg dividend table in Json.

    start_date = get_working_day_date(datetime.date.today(), -1, 3)
    end_date = get_working_day_date(datetime.date.today(), 1, 5)

    sql_query = text("Select * from aaron.bloomberg_dividend WHERE `date` >= '{}' and `date` <= '{}' AND WEEKDAY(`date`) BETWEEN 0 AND 4 ORDER BY date".format(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))

    raw_result = db.engine.execute(sql_query)
    result_data = raw_result.fetchall()     # Return [('A50', 'XIN9I Index', 0.0, datetime.date(2019, 8, 14), datetime.datetime(2019, 8, 14, 8, 0, 14)), ....]

    # Want to get all the weekdays in the middle of start_date and end_date.
    all_dates = [start_date + datetime.timedelta(days=d) for d in range(abs((end_date - start_date).days)) \
                 if (start_date + datetime.timedelta(days=d)).weekday() in range(5)]

    # dict of the results
    result_col = raw_result.keys()
    result_dict = [dict(zip(result_col,d)) for d in result_data]

    # Get unique symbols using set, then sort them.
    symbols = list(set([rd[0] for rd in result_data]))
    symbols.sort()
    return_data = []   # The data to be returned.

    for s in symbols:
        symbol_dividend_date = {}
        symbol_dividend_date["Symbol"] = s
        for d in all_dates:
            symbol_dividend_date[get_working_day_date(start_date=d, increment_decrement_val=-1, weekdays_count=1).strftime( \
                "%Y-%m-%d")] =  find_dividend(result_dict, s, d)
        return_data.append(symbol_dividend_date)
    return json.dumps(return_data)


@app.route('/BGI_Swaps')
@login_required
def BGI_Swaps():
    description = Markup("Swap values uploaded onto MT4/MT5. <br>\
   Swaps would be charged on the roll over to the next day.<br> \
    Three day swaps would be charged for FX on weds and CFDs on fri. ")
    return render_template("Standard_Single_Table.html", backgroud_Filename='css/Faded_car.jpg', Table_name="BGI_Swaps", \
                           title="BGISwaps", ajax_url=url_for("BGI_Swaps_ajax"),
                           description=description, replace_words=Markup(["Today"]))



@app.route('/BGI_Swaps_ajax', methods=['GET', 'POST'])
@login_required
def BGI_Swaps_ajax():     # Return the Bloomberg dividend table in Json.

    start_date = get_working_day_date(datetime.date.today(), -1, 5)
    sql_query = text("SELECT * FROM test.`bgi_swaps` where date >= '{}' ORDER BY Core_Symbol, Date".format(start_date.strftime("%Y-%m-%d")))
    raw_result = db.engine.execute(sql_query)
    result_data = raw_result.fetchall()
    result_col = raw_result.keys()
    return_result = [dict(zip(result_col, d)) for d in result_data]



    # Want to get unuqie dates, and sort them.
    unique_date = list(set([d['Date'] for d in return_result if 'Date' in d]))
    unique_date.sort()

    # Want to get unuqie Symbol, and sort them.
    unique_symbol = list(set([d['Core_Symbol'] for d in return_result if 'Core_Symbol' in d]))
    unique_symbol.sort()


    swap_total = [] # To store all the symbol
    for s in unique_symbol:
        swap_long_buffer = {}
        swap_short_buffer = {}
        swap_long_buffer['Symbol'] = s  # Save symbol name
        swap_long_buffer['Direction'] = "Long"
        swap_short_buffer['Symbol'] = s
        swap_short_buffer['Direction'] = "Short"
        for d in unique_date:       # Want to get Values of short and long.
            swap_long_buffer[d.strftime("%Y-%m-%d (%a)")] = find_swaps(return_result, s, d, "bgi_long")
            swap_short_buffer[d.strftime("%Y-%m-%d (%a)")] = find_swaps(return_result, s, d, "bgi_short")
        swap_total.append(swap_long_buffer)
        swap_total.append(swap_short_buffer)

    return json.dumps(swap_total)

@app.route('/MT4_Commission')
@login_required
def MT4_Commission():
    description = Markup("Swap values uploaded onto MT4/MT5. <br>\
   Swaps would be charged on the roll over to the next day.<br> \
    Three day swaps would be charged for FX on weds and CFDs on fri. ")
    return render_template("Standard_Single_Table.html", backgroud_Filename='css/Faded_car.jpg', Table_name="BGI_Swaps", \
                           title="BGISwaps", ajax_url=url_for("Mt4_Commission_ajax"),
                           description=description, replace_words=Markup([]))


@app.route('/Mt4_Commission_ajax', methods=['GET', 'POST'])
@login_required
def Mt4_Commission_ajax():     # Return the Bloomberg dividend table in Json.

    start_date = get_working_day_date(datetime.date.today(), -1, 5)
    sql_query = text("""select mt4_groups.`GROUP`, mt4_securities.`NAME`, mt4_groups.CURRENCY, mt4_groups.DEFAULT_LEVERAGE, mt4_groups.MARGIN_CALL, mt4_groups.MARGIN_STOPOUT, mt4_secgroups.`SHOW`, mt4_secgroups.TRADE, mt4_secgroups.SPREAD_DIFF, 
        mt4_secgroups.COMM_BASE, mt4_secgroups.COMM_TYPE, mt4_secgroups.COMM_LOTS, mt4_secgroups.COMM_AGENT, mt4_secgroups.COMM_AGENT_TYPE, mt4_secgroups.COMM_AGENT_LOTS  from 
        live5.mt4_groups, live5.mt4_secgroups, live5.mt4_securities
        where mt4_groups.SECGROUPS = mt4_secgroups.SECGROUPS and mt4_secgroups.TYPE = mt4_securities.TYPE and
        mt4_secgroups.`SHOW` = 1 and mt4_groups.`ENABLE` = 1
        GROUP BY `GROUP`, mt4_securities.`NAME`""")

    raw_result = db.engine.execute(sql_query)
    result_data = raw_result.fetchall()
    result_col = raw_result.keys()
    return_result = [dict(zip(result_col, d)) for d in result_data]

    return json.dumps(return_result)


# Want to show which clients got recently changed to read only.
# Due to Equity < Balance.
@app.route('/Changed_readonly')
@login_required
def Changed_readonly():
    description = Markup("")
    return render_template("Standard_Single_Table.html", backgroud_Filename='css/Faded_car.jpg', Table_name="Changed Read Only", \
                           title="Read Only Clients", ajax_url=url_for("Changed_readonly_ajax"),
                           description=description, replace_words=Markup(["Today"]))



@app.route('/Changed_readonly_ajax', methods=['GET', 'POST'])
@login_required
def Changed_readonly_ajax():

    # Which Date to start with. We want to count back 1 day. 
    start_date = get_working_day_date(datetime.date.today(), -1, 1)
    sql_query = text("Select * from test.changed_read_only WHERE `date` >= '{}' order by Date DESC".format(start_date.strftime("%Y-%m-%d")))
    raw_result = db.engine.execute(sql_query)
    result_data = raw_result.fetchall()     # Return Result
    # dict of the results
    result_col = raw_result.keys()
    # Clean up the data. Date.
    result_data_clean = [[a.strftime("%Y-%m-%d %H:%M:%S") if isinstance(a, datetime.datetime) else a for a in d] for d in result_data]
    result_dict = [dict(zip(result_col,d)) for d in result_data_clean]

    return json.dumps(result_dict)


# [{'Core_Symbol': '.A50', 'bgi_long': '0.000000000000', 'bgi_short': '0.000000000000', 'Date': datetime.date(2019, 8, 13)},....]
def find_swaps(data, symbol, date, Long_Short):
    for d in data:
        if 'Core_Symbol' in d and d['Core_Symbol'] == symbol:
            if 'Date' in d and d['Date'] == date:
                if isinstance(d[Long_Short], float) or isinstance(d[Long_Short], int) or Check_Float(d[Long_Short]):
                    return "{:.4f}".format(float(d[Long_Short]))

                else:
                    return d[Long_Short]
    return 'X'


# Get the dividend value from the list of dicts.
def find_dividend(data, symbol, date):

    for d in data:
        if "mt4_symbol" in d and d["mt4_symbol"] == symbol and \
            "date" in d and d["date"] == date:
            return_val = ""
            if (get_working_day_date(start_date=date, increment_decrement_val=-1, weekdays_count=1) == datetime.date.today()):
                return_val += "Today"   # Want to append words, for javascript to know which to highlight
            if d["dividend"] == 0:
                return "{}-".format(return_val)
            else:
                return "{}{}".format(d["dividend"], return_val)
    else:
        return "X"

# Want to either count forward or backwards, the number of weekdays.
def get_working_day_date(start_date, increment_decrement_val, weekdays_count):

    return_date = start_date
    backtrace_days = 0
    weekday_count = 0   # how many weekdays have we looped thru
    while weekday_count < weekdays_count: # How many weekdays do we want to go back by?
        backtrace_days += increment_decrement_val   # Either + 1 or -1
        return_date = start_date + datetime.timedelta(days=backtrace_days)
        if return_date.weekday() in [0,1,2,3,4]: # We will count it if weekdays.
            weekday_count += 1

    return return_date



# Helper function to check if string is json
def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except (ValueError):
    return False
  return True


# Input: sql_query.
# Return a Dict, using Zip for the results and the col names.
def Query_SQL_db_engine(sql_query):
    raw_result = db.engine.execute(sql_query)
    result_data = raw_result.fetchall()
    result_data_decimal = [[float(a) if isinstance(a, decimal.Decimal) else a for a in d ] for d in result_data]    # correct The decimal.Decimal class to float.
    result_col = raw_result.keys()
    zip_results = [dict(zip(result_col,d)) for d in result_data_decimal]
    return zip_results


# Async Call to send email.
@async
def async_send_email(To_recipients, cc_recipients, Subject, HTML_Text, Attachment_Name):
    Send_Email(To_recipients, cc_recipients, Subject, HTML_Text, Attachment_Name)


# Async Call to send telegram message.
@async
def async_Post_To_Telegram(Bot_token, text_to_tele, Chat_IDs):
    Post_To_Telegram(Bot_token, text_to_tele, Chat_IDs)

# Async update the runtime table for update.
@async
def async_Update_Runtime(Tool):
    # Want to update the runtime table to ensure that tool is running.
    sql_insert = "INSERT INTO  aaron.`monitor_tool_runtime` (`Monitor_Tool`, `Updated_Time`) VALUES" + \
                 " ('{Tool}', now()) ON DUPLICATE KEY UPDATE Updated_Time=now()".format(Tool=Tool)
    raw_insert_result = db.engine.execute(sql_insert)
    #print("Updating Runtime for Tool: {}".format(Tool))


# Helper function to do a time check.
# Return "Update Slow<br> time" if it is more then 10 mins difference.
def Time_difference_Check(time_to_check):
    time_now = datetime.datetime.now()  # Get the time now.
    if not isinstance(time_to_check, datetime.datetime):
        return "Error: Not datetime.datetime object"

    if abs((time_now - time_to_check).total_seconds()) > TIME_UPDATE_SLOW_MIN*60: # set the update to 10 mins.
        return time_to_check.strftime("<b>Update Slow</b><br>%Y-%m-%d<br>%H:%M:%S")
    else:
        return time_to_check.strftime("%Y-%m-%d<br>%H:%M:%S")


# Query SQL and return the Zip of the results to get a record.
def Query_SQL_Return_Record(SQL_Query):
    raw_result = db.engine.execute(SQL_Query)
    result_data = raw_result.fetchall()
    result_col = raw_result.keys()
    collate = [dict(zip(result_col, a)) for a in result_data]
    return collate




def create_table_fun(table_data):

    T = create_table()
    table = T(table_data, classes=["table", "table-striped", "table-bordered", "table-hover", "table-sm"])
    if (len(table_data) > 0) and isinstance(table_data[0], dict):
        for c in table_data[0]:
            if c != "\n":
                table.add_column(c, Col(c, th_html_attrs={"style": "background-color:#afcdff; word-wrap:break-word"}))
    return table

# Simple way of returning time string.
def time_now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")