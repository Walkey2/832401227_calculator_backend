# Backend Python Code Style Guide
Reference standard: PEP 8
1. Use 4 spaces for indentation.
2. Use snake_case for functions and variables; use PascalCase for class names.
3. Line length limit: 88 characters.
4. Import order: standard library -> third-party library -> local modules.
5. Add docstrings for functions.
6. Catch specific exceptions, avoid bare except statements.
7. Use uppercase for constants.
8. Separate module responsibilities: routing, service, database.
9. Never use eval / exec to execute user input expressions.
