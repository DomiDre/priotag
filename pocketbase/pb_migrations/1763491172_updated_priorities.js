/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "createRule": "@request.auth.id = userId || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "deleteRule": "@request.auth.id = userId || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "listRule": "@request.auth.id = userId || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "updateRule": "@request.auth.id = userId || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)",
    "viewRule": "@request.auth.id = userId || @request.auth.role = \"super_admin\" || (@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id)"
  }, collection)

  // add field
  collection.fields.addAt(6, new Field({
    "cascadeDelete": false,
    "collectionId": "pbc_2630615650",
    "hidden": false,
    "id": "relation272652678",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "institution_id",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // update collection data
  unmarshal({
    "createRule": "@request.auth.id != \"\"",
    "deleteRule": "@request.auth.id = userId || @request.auth.role = \"admin\"",
    "listRule": "@request.auth.id = userId || @request.auth.role = \"admin\"",
    "updateRule": "@request.auth.id = userId || @request.auth.role = \"admin\"",
    "viewRule": "@request.auth.id = userId || @request.auth.role = \"admin\""
  }, collection)

  // remove field
  collection.fields.removeById("relation272652678")

  return app.save(collection)
})
