/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_380247205")

  // update collection data
  unmarshal({
    "listRule": "@request.auth.institution_id = id || @request.auth.role = \"service\"",
    "viewRule": "@request.auth.institution_id = id || @request.auth.role = \"service\""
  }, collection)

  // remove field
  collection.fields.removeById("_clone_1AZk")

  // remove field
  collection.fields.removeById("_clone_0eIR")

  // remove field
  collection.fields.removeById("_clone_ARHd")

  // remove field
  collection.fields.removeById("_clone_hCTH")

  // add field
  collection.fields.addAt(1, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "_clone_J2Ek",
    "max": 0,
    "min": 0,
    "name": "name",
    "pattern": "",
    "presentable": true,
    "primaryKey": false,
    "required": true,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(2, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "_clone_0HQr",
    "max": 0,
    "min": 0,
    "name": "short_code",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": true,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(3, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "_clone_yCJI",
    "max": 0,
    "min": 0,
    "name": "admin_public_key",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": true,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(4, new Field({
    "hidden": false,
    "id": "_clone_UtuO",
    "maxSize": 0,
    "name": "settings",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_380247205")

  // update collection data
  unmarshal({
    "listRule": "@request.auth.institution_id = id",
    "viewRule": "@request.auth.institution_id = id"
  }, collection)

  // add field
  collection.fields.addAt(1, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "_clone_1AZk",
    "max": 0,
    "min": 0,
    "name": "name",
    "pattern": "",
    "presentable": true,
    "primaryKey": false,
    "required": true,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(2, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "_clone_0eIR",
    "max": 0,
    "min": 0,
    "name": "short_code",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": true,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(3, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "_clone_ARHd",
    "max": 0,
    "min": 0,
    "name": "admin_public_key",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": true,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(4, new Field({
    "hidden": false,
    "id": "_clone_hCTH",
    "maxSize": 0,
    "name": "settings",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  // remove field
  collection.fields.removeById("_clone_J2Ek")

  // remove field
  collection.fields.removeById("_clone_0HQr")

  // remove field
  collection.fields.removeById("_clone_yCJI")

  // remove field
  collection.fields.removeById("_clone_UtuO")

  return app.save(collection)
})
