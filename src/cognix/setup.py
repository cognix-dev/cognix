from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cognix",
    version="0.1.0",
    author="Cognix Dev",
    author_email="dev@cognix.dev",
    description="AI development assistant with persistent memory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cognix-dev/cognix",
    project_urls={
        "Bug Tracker": "https://github.com/cognix-dev/cognix/issues",
        "Documentation": "https://github.com/cognix-dev/cognix",
        "Source Code": "https://github.com/cognix-dev/cognix",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "anthropic>=0.18.0",
        "openai>=1.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cognix=cognix.cli:main",
        ],
    },
    keywords="ai artificial-intelligence cli development-tools assistant memory",
    zip_safe=False,
)
