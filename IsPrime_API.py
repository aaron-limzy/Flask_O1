import requests
import json


def is_prime_query_AccDetails():
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
    for s in dict_response:
        if "groupName" in s and s["groupName"] ==  "Blackwell Global BVI Risk 2":   # Making sure its the right account.
            lp = "Is Prime Terminus"
            account_balance = s["collateral"]
            account_margin_level = 1 / s["marginUtilisation"]   * 100   # Need to invert this to be E/M
            account_margin_use = s["requirement"]
            account_floating = s["unrealisedPnl"]
            account_equity = s["netEquity"]
            account_free_margin = s["preDeliveredCollateral"]
            account_credit = 0
            account_margin_call = 100
            account_stop_out = 0
            account_stop_out_amount = 0

            sql_insert = "INSERT INTO  aaron.`bgi_hedge_lp_summary_test` \
            (`lp`, `deposit`, `pnl`, `equity`, `total_margin`, `free_margin`, `credit`, `margin_call(E/M)`, `stop_out(E/M)`, `stop_out_amount`, `updated_time(SGT)`) VALUES" \
                         " ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',NOW()) ".format(lp, account_balance, account_floating, account_equity, account_margin_use, account_free_margin, \
                                                                                                  account_credit, account_margin_call,account_stop_out, account_stop_out_amount)
            SQL_LP_Footer = " ON DUPLICATE KEY UPDATE deposit = VALUES(deposit), pnl = VALUES(pnl), equity = VALUES(equity), total_margin = VALUES(total_margin), free_margin = VALUES(free_margin), `updated_time(SGT)` = VALUES(`updated_time(SGT)`), credit = VALUES(credit), `margin_call(E/M)` = VALUES(`margin_call(E/M)`),`stop_out(E/M)` = VALUES(`stop_out(E/M)`) ";

            sql_insert += SQL_LP_Footer

            print(sql_insert)
            #raw_insert_result = db.engine.execute(sql_insert)



