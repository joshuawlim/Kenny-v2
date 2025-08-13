"""
Setup script for the Kenny Agent SDK package.

This package provides the foundational classes and utilities for creating
agents in the Kenny v2 multi-agent system.
"""

from setuptools import setup, find_packages

# Read the README file for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kenny-agent-sdk",
    version="0.1.0",
    author="Kenny v2 Team",
    author_email="team@kenny-v2.local",
    description="Base framework for building agents in the Kenny v2 system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kenny-v2/agent-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="agent, multi-agent, framework, kenny, personal-assistant",
    project_urls={
        "Bug Reports": "https://github.com/kenny-v2/agent-sdk/issues",
        "Source": "https://github.com/kenny-v2/agent-sdk",
        "Documentation": "https://github.com/kenny-v2/agent-sdk/docs",
    },
)
