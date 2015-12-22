Financial Assistance Scripts

These scripts can be used to retrieve, clean, and analyze financial assistance submissions.

Requirements
- Zendesk agent username/password
- Python 2.7+

Scripts
- get_submissions.py: Uses Zendesk API to retrieve, parse, and store data
- clean_submissions.py: Removes test submissions, cleans country names, matches IP address to country code, and
  filters income outliers (>$100K)
- analyze_submisisons.py: Outputs basic stats on the submissions.

TODO
- Fix logging for all scripts
- Report outliers (instead of dropping them with no notice)
- General code organization and quality cleanup
- Visualizations!?
