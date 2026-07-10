#!/bin/bash
cd /c/Users/rayxc/Documents/R
until grep -q "OFFICE_PROGRAM_COMPLETE" _bestrec_run/run_office_program_driver.log 2>/dev/null; do sleep 120; done
# pass 2: encode now works; idonly/floor JSONs exist and are skipped; text arms run for real
bash _bestrec_run/run_office_program.sh > _bestrec_run/run_office_program_driver_pass2.log 2>&1
echo "OFFICE_PASS2_COMPLETE"
