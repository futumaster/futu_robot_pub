from futu import *

def print_hi():
    # Use a breakpoint in the code line below to debug your script.
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    quote_ctx.request_history_kline()
    quote_ctx.close()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi()