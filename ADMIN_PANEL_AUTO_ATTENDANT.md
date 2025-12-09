# Auto Attendant Management via Admin Panel

## Overview

The Auto Attendant (IVR - Interactive Voice Response) system can now be fully managed through the web admin panel, eliminating the need for terminal access or manual configuration file editing.

## Accessing Auto Attendant Settings

1. Open the Admin Panel at `http://YOUR_PBX_IP:8080/admin/`
2. Click on the **"Auto Attendant"** tab in the navigation bar

## Configuration Options

### General Settings

Configure the basic behavior of your auto attendant:

- **Enable Auto Attendant**: Toggle to enable/disable the auto attendant system
- **Extension Number**: The extension number that callers dial to reach the auto attendant (typically `0`)
- **Timeout (seconds)**: How long to wait for DTMF input before repeating the menu (5-60 seconds)
- **Max Retries**: Maximum number of invalid attempts before transferring to operator (1-10 attempts)

Click **"💾 Save Settings"** to apply changes.

### Menu Options

Menu options define what happens when callers press digits on their phone.

#### Adding a Menu Option

1. Click **"➕ Add Menu Option"** button
2. Fill in the form:
   - **Digit**: The digit callers will press (0-9, *, or #)
   - **Destination Extension**: Where to transfer the call (extension, queue, or feature code)
   - **Description**: Human-readable description (e.g., "Sales Department")
3. Click **"Add Menu Option"**

**Example Configuration:**
```
Digit: 1
Destination: 1001
Description: Sales Department

Digit: 2
Destination: 1002
Description: Technical Support

Digit: 0
Destination: 1000
Description: Operator
```

#### Editing a Menu Option

1. Click **"✏️ Edit"** next to the menu option
2. Update the destination or description
3. Click **"Update Menu Option"**

#### Deleting a Menu Option

1. Click **"🗑️ Delete"** next to the menu option
2. Confirm the deletion

## Audio Prompts

The auto attendant requires audio files to play to callers:

### Required Files (located in `auto_attendant/` directory):

- `welcome.wav` - Initial greeting when call is answered
- `main_menu.wav` - Menu options announcement
- `invalid.wav` - Played when invalid digit is pressed
- `timeout.wav` - Played when no input is received

### Generating Audio Prompts

Use the provided script to generate professional voice prompts:

```bash
cd /home/runner/work/PBX/PBX
python3 scripts/generate_espeak_voices.py
```

Or create custom recordings and place them in the `auto_attendant/` directory.

## API Endpoints

For programmatic access, the following REST API endpoints are available:

### Get Configuration
```bash
GET /api/auto-attendant/config
```

### Update Configuration
```bash
PUT /api/auto-attendant/config
Content-Type: application/json

{
  "enabled": true,
  "extension": "0",
  "timeout": 10,
  "max_retries": 3
}
```

### Get Menu Options
```bash
GET /api/auto-attendant/menu-options
```

### Add Menu Option
```bash
POST /api/auto-attendant/menu-options
Content-Type: application/json

{
  "digit": "1",
  "destination": "1001",
  "description": "Sales Department"
}
```

### Update Menu Option
```bash
PUT /api/auto-attendant/menu-options/{digit}
Content-Type: application/json

{
  "destination": "1002",
  "description": "Updated Description"
}
```

### Delete Menu Option
```bash
DELETE /api/auto-attendant/menu-options/{digit}
```

## Best Practices

1. **Keep it Simple**: Limit menu options to 5-7 choices for better user experience
2. **Use Clear Audio**: Ensure audio prompts are clear and professional
3. **Test Thoroughly**: Call the auto attendant and test all menu options
4. **Provide an Operator Option**: Always include an option to reach a live person (typically 0)
5. **Consider Peak Hours**: Set appropriate timeout values based on your call volume
6. **Update Regularly**: Keep menu options current with your organization's structure

## Troubleshooting

### Auto Attendant Not Working

1. Verify it's enabled in the configuration
2. Check that the extension number is correct
3. Ensure audio files exist in `auto_attendant/` directory
4. Verify menu options are configured
5. Check PBX logs for errors

### Callers Not Hearing Audio

1. Verify audio files exist and are in WAV format
2. Check file permissions on `auto_attendant/` directory
3. Regenerate audio prompts using the script
4. Check audio file paths in configuration

### Menu Options Not Working

1. Verify destinations are valid extensions or queues
2. Check that extensions/queues are registered and active
3. Test DTMF tone detection on your phone
4. Review PBX logs for routing errors

## Migration from Terminal Configuration

If you previously configured the auto attendant via terminal:

1. Your existing configuration in `config.yml` will be loaded automatically
2. Use the admin panel to make changes going forward
3. The admin panel updates the in-memory configuration
4. Consider documenting your menu structure for reference

## Security Notes

- Access to the admin panel should be restricted to authorized users only
- Consider implementing HTTPS for the admin panel in production
- Menu options should only point to valid, authorized destinations
- Regular audits of auto attendant configuration are recommended
