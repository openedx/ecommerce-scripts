# Upgrade Deadline Repair

This directory contains a Python 3.6.x script for populating upgrade deadlines on
ecommerce seats. Seats must have non-empty upgrade deadlines in order for the system
to work correctly. In spite of this, the ecommerce service has allowed seats to
be created without upgrade deadlines. The script in this directory pulls course
runs from the discovery service, identifies course runs with seats that need to
be updated, then uses the ecommerce service's course admin tool (CAT) in a headless
browser to update these course runs.
