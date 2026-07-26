# Contributing to DataVeil

Thank you for your interest in contributing to DataVeil! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How Can I Contribute?

### Reporting Bugs

- Check if the bug has already been reported in [Issues](https://github.com/JediKinght9527/dataveil/issues)
- Use the bug report template when creating a new issue
- Include: OS, Python version, DataVeil version, steps to reproduce, expected vs actual behavior

### Suggesting Features

- Check if the feature has already been suggested
- Explain the use case and why it would benefit most users
- Consider if it aligns with the project's scope (lightweight, privacy-first)

### Pull Requests

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**:
   - Follow the existing code style (ruff)
   - Add tests for new functionality
   - Update documentation if needed
4. **Run tests**: `pytest tests/ -v`
5. **Run linter**: `ruff check dv/ tests/`
6. **Commit**: Use clear, descriptive commit messages
7. **Push** and create a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/JediKinght9527/dataveil.git
cd dataveil

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check dv/ tests/
```

### Code Style

- We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Line length: 100 characters
- Python 3.9+ compatibility required
- Type hints encouraged but not strictly enforced

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs when applicable

### Areas We Need Help

- **Detection Rules**: More code-aware patterns (Go, Rust, Java-specific secrets)
- **IDE Plugins**: VS Code, Cursor, JetBrains extensions
- **Documentation**: Tutorials, videos, translations
- **Testing**: More edge cases, performance benchmarks
- **Rust Core**: Performance-critical components in Rust

### Questions?

- Open a [Discussion](https://github.com/JediKinght9527/dataveil/discussions)
- Email: maintainers@dataveil.dev

Thank you for contributing! 🎉
