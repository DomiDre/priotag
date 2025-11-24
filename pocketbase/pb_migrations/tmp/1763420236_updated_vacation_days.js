/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3854395317")

  // add field
  collection.fields.addAt(5, new Field({
    "cascadeDelete": false,
    "collectionId": "pbc_9876543210",
    "hidden": false,
    "id": "relation9876543212",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "institution_id",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  // update create rule to include institution check
  // Note: For create, we check that user is institution_admin or super_admin
  // The institution_id validation happens at application level
  collection.createRule = "@request.auth.role = \"institution_admin\" || @request.auth.role = \"super_admin\""

  // update list rule to filter by institution
  collection.listRule = "@request.auth.role = \"super_admin\" || @request.auth.institution_id = institution_id"

  // update view rule to filter by institution
  collection.viewRule = "@request.auth.role = \"super_admin\" || @request.auth.institution_id = institution_id"

  // update update rule to include institution check
  collection.updateRule = "(@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id) || @request.auth.role = \"super_admin\""

  // update delete rule to include institution check
  collection.deleteRule = "(@request.auth.role = \"institution_admin\" && @request.auth.institution_id = institution_id) || @request.auth.role = \"super_admin\""

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3854395317")

  // remove field
  collection.fields.removeById("relation9876543212")

  // restore original rules
  collection.createRule = "@request.auth.role = \"admin\""
  collection.listRule = "@request.auth.id != \"\""
  collection.viewRule = "@request.auth.id != \"\""
  collection.updateRule = "@request.auth.role = \"admin\""
  collection.deleteRule = "@request.auth.role = \"admin\""

  return app.save(collection)
})
