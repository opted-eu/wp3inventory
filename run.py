from flaskinventory import create_app
import argparse
parser = argparse.ArgumentParser(description='Specify config file (json)')
parser.add_argument('--config', type=str)
args = parser.parse_args()

if args.config:
    app = create_app(config_json=args.config)
else:
    app = create_app()

if __name__ == '__main__':
    app.run(debug=True)