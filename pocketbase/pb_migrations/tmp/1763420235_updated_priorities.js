/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // add field
  collection.fields.addAt(10, new Field({
    "cascadeDelete": false,
    "collectionId": "pbc_9876543210",
    "hidden": false,
    "id": "relation9876543211",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "institution_id",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  // update list rule to filter by institution
  collection.listRule = "@request.auth.role = \"super_admin\" || @request.auth.institution_id = institution_id"

  // update view rule to filter by institution
  collection.viewRule = "@request.auth.role = \"super_admin\" || @request.auth.institution_id = institution_id"

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_661221447")

  // remove field
  collection.fields.removeById("relation9876543211")

  // restore original list rule
  collection.listRule = null

  // restore original view rule
  collection.viewRule = null

  return app.save(collection)
})
