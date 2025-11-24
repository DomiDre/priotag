/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_380247205")

  // update collection data
  unmarshal({
    "viewQuery": "SELECT id, name, short_code, admin_public_key, settings FROM institutions WHERE active = true"
  }, collection)

  // remove field
  collection.fields.removeById("_clone_TAnQ")

  // remove field
  collection.fields.removeById("_clone_7h1i")

  // remove field
  collection.fields.removeById("_clone_QKrF")

  // remove field
  collection.fields.removeById("_clone_ATHh")

  // remove field
  collection.fields.removeById("_clone_6RgA")

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

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_380247205")

  // update collection data
  unmarshal({
    "viewQuery": "SELECT id, name, short_code, admin_public_key, settings, active FROM institutions"
  }, collection)

  // add field
  collection.fields.addAt(1, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "_clone_TAnQ",
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
    "id": "_clone_7h1i",
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
    "id": "_clone_QKrF",
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
    "id": "_clone_ATHh",
    "maxSize": 0,
    "name": "settings",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  // add field
  collection.fields.addAt(5, new Field({
    "hidden": false,
    "id": "_clone_6RgA",
    "name": "active",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "bool"
  }))

  // remove field
  collection.fields.removeById("_clone_1AZk")

  // remove field
  collection.fields.removeById("_clone_0eIR")

  // remove field
  collection.fields.removeById("_clone_ARHd")

  // remove field
  collection.fields.removeById("_clone_hCTH")

  return app.save(collection)
})
