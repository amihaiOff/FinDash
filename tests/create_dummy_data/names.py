# Define the list of payees, categories, and category groups
payees = ['Supermarket', 'Restaurant', 'Gas Station', 'Clothing Store',
          'Utility Bill', 'Electronics Store', 'Gym', 'Pharmacy']

categories = ['Groceries', 'Dining', 'Transportation', 'Shopping', 'Bills']

category_groups = ['Essentials', 'Entertainment', 'Transportation']

accounts = ['Bank Account', 'Credit Card']

category_groups_mapping = {
    'Groceries': 'Essentials',
    'Dining': 'Entertainment',
    'Transportation': 'Transportation',
    'Shopping': 'Entertainment',
    'Bills': 'Essentials'
}

# Define the mapping between payees and categories
payee_category_mapping = {
    'Supermarket': 'Groceries',
    'Restaurant': 'Dining',
    'Gas Station': 'Transportation',
    'Clothing Store': 'Shopping',
    'Utility Bill': 'Bills',
    'Electronics Store': 'Shopping',
    'Gym': 'Bills',
    'Pharmacy': 'Bills'
}

# Define the mapping between payees and account types
payee_account_type_mapping = {
    'Supermarket': 'Bank Account',
    'Restaurant': 'Credit Card',
    'Gas Station': 'Bank Account',
    'Clothing Store': 'Credit Card',
    'Utility Bill': 'Bank Account',
    'Electronics Store': 'Credit Card',
    'Gym': 'Bank Account',
    'Pharmacy': 'Credit Card'
}
