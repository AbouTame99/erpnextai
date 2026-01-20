from setuptools import setup, find_packages

with open("README.md", "r") as f:
	long_description = f.read()

setup(
	name="erpnextai",
	version="1.0.0",
	description="AI for ERPNext you can use it to talk with ai with all your erpnext info",
	long_description=long_description,
	long_description_content_type="text/markdown",
	author="Aboubaker Tamessouct",
	author_email="abou.tame99@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=[
		"google-generativeai"
	],
)
