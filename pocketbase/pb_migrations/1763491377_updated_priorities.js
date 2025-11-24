/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_aORyEH3vd7` ON `priorities` (\n  `userId`,\n  `month`,\n  `identifier`\n)",
      "CREATE INDEX `idx_K0Wv8uuGxZ` ON `priorities` (`institution_id`)"
    ]
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "indexes": [
      "CREATE UNIQUE INDEX `idx_aORyEH3vd7` ON `priorities` (\n  `userId`,\n  `month`,\n  `identifier`\n)"
    ]
  }, collection)

  return app.save(collection)
})
