from flaskinventory import create_app

app = create_app(config_json='config.json')

if __name__ == '__main__':
    app.run(debug=True)