__author__ = 'yaronshahverdi'

import sys
import requests
import json
import HTMLParser

class Product():
    def __init__(self, name, id, price):
        self.name = name
        self.id = id
        self.price = price

api_key = "a73121520492f88dc3d33daf2103d7574f1a3166"

x = float(sys.argv[1])
n = float(sys.argv[2])

error = False

# get all price values that exist in the database
price_facet_values = requests.get("http://api.zappos.com/Search?term=&facets=[\"price\"]&excludes=[\"results\"]&key=%s" % api_key)
price_facet_values = json.loads(price_facet_values.text)
if price_facet_values['statusCode'] == '401':
    print "API requests are being throttled"
    sys.exit(1)
price_facet_values = price_facet_values['facets'][0]['values']

all_prices = []
for price in price_facet_values:
    all_prices.append(float(price['name']))

# try to get a price for which there are at least twice the amount of results than we want (because there duplicates in the database)
product_price = round(n/x,2)
total_results = 0
while (product_price not in all_prices) or (round(product_price % 1,2) not in [0,0.5,0.99]) or (total_results < 2 * int(x)):
    cents = round(product_price % 1,2)
    if cents  in [0,0.5,0.99]:
        product_price = round(product_price - 0.50, 2)
    elif cents < 0.25:
        product_price = round(product_price - 0.01,2)  # round down to .00
    elif cents < 0.50:
        product_price = round(product_price + 0.01,2)   # round up to .50
    elif cents < 0.75:
        product_price = round(product_price - 0.01,2)   # round down to .50
    else:
        product_price = round(product_price + 0.01,2)   # round up to .00
    if (product_price in all_prices) and round(product_price % 1,2) in (0,0.5,0.99):
        r = requests.get("http://api.zappos.com/Search?term=&filters={\"price\":[\"%s\"]}&key=%s" % (str(product_price),api_key))
        product_data = json.loads(r.text)
        total_results = int(product_data['totalResultCount'])

x = int(x)
n = int(n)

products = []
product_ids = []

# set result limit for page requests based on number of items we are looking for
if x < 50:
    result_limit = 10
elif x < 100:
    result_limit = 25
else:
    result_limit = 50

# add products to our list of products
if x <= result_limit:
    pages = 1
    r = requests.get("http://api.zappos.com/Search?term=&filters={\"price\":[\"%s\"]}&key=%s" % (str(product_price),api_key))
    product_data = json.loads(r.text)
    for i in xrange(int(x)):
        if product_data['results'][i]['productId'] not in product_ids:
            prod_detail = product_data['results'][i]
            products.append(Product(HTMLParser.HTMLParser().unescape(prod_detail['productName']), prod_detail['productId'], float(prod_detail['price'].lstrip('$'))))
            product_ids.append(prod_detail['productId'])
else:
    pages = x/result_limit
    leftover = x % result_limit
    for page_number in xrange(pages):
        r = requests.get("http://api.zappos.com/Search?term=&limit=%s&page=%s&filters={\"price\":[\"%s\"]}&key=%s" % (result_limit,str(page_number),str(product_price),api_key))
        product_data = json.loads(r.text)
        for prod in product_data['results']:
            if prod['productId'] not in product_ids:
                products.append(Product(HTMLParser.HTMLParser().unescape(prod['productName']), prod['productId'], float(prod['price'].lstrip('$'))))
                product_ids.append(prod['productId'])
                if len(products) == x:
                    break

# because we ignored duplicates, we still need to add products until we have the amount we would like (x)
while len(products) != x:
    r = requests.get("http://api.zappos.com/Search?term=&limit=%s&page=%s&filters={\"price\":[\"%s\"]}&key=%s" % (result_limit,str(pages),str(product_price),api_key))
    product_data = json.loads(r.text)
    for prod in product_data['results']:
        if prod['productId'] not in product_ids:
            products.append(Product(HTMLParser.HTMLParser().unescape(prod['productName']), prod['productId'], float(prod['price'].lstrip('$'))))
            product_ids.append(prod['productId'])
            if len(products) == x:
                break
    pages += 1
    if total_results < (result_limit*pages):
        error = True
        break

# print the products we found
total = 0
for i in xrange(len(products)):
    p = products[i]
    print "Product %s:  ($%.2f)  (ID:%s)\t%s" % (str(i+1),float(p.price),p.id, p.name)
    total += p.price

if error:
    print "ERROR: Did not find enough results -- %d missing" % (x - len(products))


if total > n:
    print "\nTotal of $%.2f (+ $%.2f from desired dollar amount)" % (total,abs(n-total))
elif total == n:
    print "\nTotal of $%.2f" % total
else:
    print "\nTotal of $%.2f (- $%.2f from desired dollar amount)" % (total,n-total)