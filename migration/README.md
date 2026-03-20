# Migration Guide

Navigate to the `migration/` directory.

You will find two directories:

- `mysql/`
- `mongodb/`

Depending on which database you are using, run the appropriate migration script.

### For MySQL

```sh
python3 -m mysql
```

### For MongoDB

```sh
python3 -m mongodb
```

---

## Notes

- Make sure your database configuration is correct before running migrations.
- It is recommended to **backup your database** before proceeding.
- Migration scripts will update your database structure to match the latest version.