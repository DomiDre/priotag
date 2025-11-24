/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3854395317")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_1l9M8fXdOn` ON `vacation_days` (`date`)",
      "CREATE INDEX `idx_fqPWJwqrMr` ON `vacation_days` (`type`)",
      "CREATE INDEX `idx_XeYKdEJiW2` ON `vacation_days` (`institution_id`)"
    ]
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3854395317")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_1l9M8fXdOn` ON `vacation_days` (`date`)",
      "CREATE INDEX `idx_fqPWJwqrMr` ON `vacation_days` (`type`)"
    ]
  }, collection)

  return app.save(collection)
})
