import sys
from src.idcardreader_package.idcardreader import get_user_data

if __name__ == '__main__':
    debug = "--debug" in sys.argv
    customer_data, error_code = get_user_data(debug=debug)
    print("customer_data {}".format(customer_data))
    print("error_code {}".format(error_code))
