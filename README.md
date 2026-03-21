# Water Utility Sensor

Home Assistant integration for scraping water meter data from various water utility providers.

## Supported Providers

- **WODKAN Krzeszowice** (ibo.wikkrzeszowice.pl)

## Installation

### Via HACS (recommended)
1. Add this repository to HACS as a custom repository
2. Search for "Water Utility Sensor" and install
3. Restart Home Assistant

### Manual Installation
1. Copy `custom_components/water_utility/` to your Home Assistant's `custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Navigate to Settings > Devices & Services > Add Integration
2. Search for "Water Utility Sensor"
3. Select your water provider
4. Enter your IBO portal credentials

## Requirements

- Python 3.10+
- playwright
- PyMuPDF

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## License

MIT License
