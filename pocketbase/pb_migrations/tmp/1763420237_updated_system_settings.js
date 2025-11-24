/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // add field for super admin magic word
  collection.fields.addAt(5, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text9876543213",
    "max": 0,
    "min": 0,
    "name": "super_admin_magic_word",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  // add field for default institution
  collection.fields.addAt(6, new Field({
    "cascadeDelete": false,
    "collectionId": "pbc_9876543210",
    "hidden": false,
    "id": "relation9876543214",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "default_institution_id",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3806592213")

  // remove fields
  collection.fields.removeById("text9876543213")
  collection.fields.removeById("relation9876543214")

  return app.save(collection)
})
