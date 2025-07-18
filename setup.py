"""
Setup script for VibeSafe
"""
from setuptools import setup, find_packages
import platform

# Base requirements
install_requires = [
    "cryptography>=41.0.0",
    "click>=8.1.0",
]

# Platform-specific requirements
extras_require = {
    "macos": [
        "pyobjc-core>=9.0",
        "pyobjc-framework-Security>=9.0",
        "pyobjc-framework-LocalAuthentication>=9.0",
        "pyobjc-framework-AuthenticationServices>=9.0",
        "pyobjc-framework-WebKit>=9.0",
    ],
    "fido2": [
        "fido2>=1.1.0",
    ],
    "dev": [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "black>=23.0.0",
        "flake8>=6.0.0",
    ],
}

# Add platform-specific deps automatically
if platform.system() == "Darwin":
    install_requires.extend(extras_require["macos"])

setup(
    name="vibesafe",
    version="1.0.0",
    author="VibeSafe Team",
    author_email="security@vibesafe.io",
    description="Secure secrets manager with passkey protection for Claude Code",
    long_description="See README.md for details",
    long_description_content_type="text/markdown",
    url="https://github.com/vibesafe/vibesafe",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "vibesafe=vibesafe:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)