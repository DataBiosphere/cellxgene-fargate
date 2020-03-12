SHELL=/bin/bash

%: %.template.py .FORCE
	python $< $@
.FORCE:

# The template output file depends on the template file, of course, as well as the environment. To be safe we force the
# template creation. This is what the fake .FORCE target does. It still is necessary to declare a target's dependency on
# a template to ensure correct ordering.
